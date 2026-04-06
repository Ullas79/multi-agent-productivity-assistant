# app.py - Run with: streamlit run app.py
import json
import uuid

import requests
import streamlit as st

# Configuration
API_URL = "http://localhost:8000/api/chat"

st.set_page_config(page_title="AgentFlow HMS", page_icon="🏥", layout="wide")

st.title("🏥 AgentFlow: Hospital Management System")
st.markdown(
    "Multi-Agent AI coordinating Clinical Tasks, Appointments, and Patient Records."
)

# Initialize Session State
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar: System Status & Demo prompts
with st.sidebar:
    st.header("⚙️ Agent Activity Logs")
    st.success("Orchestrator Agent: Online")
    st.success("EHR Database (AlloyDB): Connected")
    st.success("Scheduling Sub-Agent: Online")

    st.divider()
    st.markdown("**Example Prompts to Try:**")
    st.code("What appointments do we have tomorrow?")
    st.code("Add a clinical task to check John Doe's vitals at 2 PM. Priority: High.")
    st.code("Pull up the patient record for Emily Chen.")

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input
if prompt := st.chat_input("Ask the Hospital Orchestrator..."):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Show AI response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        # UI polish: show "agents thinking"
        with st.status(
            "Orchestrator is routing your request...", expanded=True
        ) as status:
            st.write("Calling Gemini 2.0 Flash...")
            st.write("Querying AlloyDB...")

            try:
                # Stream SSE response from FastAPI backend
                with requests.post(
                    API_URL,
                    json={"message": prompt, "session_id": st.session_state.session_id},
                    stream=True,
                    timeout=120,
                ) as r:
                    r.raise_for_status()
                    for line in r.iter_lines():
                        if line:
                            decoded_line = line.decode("utf-8")
                            if decoded_line.startswith("data: "):
                                payload = decoded_line[6:]
                                try:
                                    data = json.loads(payload)
                                except json.JSONDecodeError:
                                    continue

                                if data.get("type") == "text":
                                    full_response += data.get("content", "")
                                    message_placeholder.markdown(full_response + "▌")

                                if data.get("type") == "session_id" and data.get(
                                    "session_id"
                                ):
                                    st.session_state.session_id = data["session_id"]

                                if data.get("type") == "done":
                                    break

                status.update(
                    label="Workflow Complete!", state="complete", expanded=False
                )

                if not full_response.strip():
                    full_response = "No response received from orchestrator."

                message_placeholder.markdown(full_response)
                st.session_state.messages.append(
                    {"role": "assistant", "content": full_response}
                )

            except Exception:
                status.update(label="API Error", state="error")
                st.error("Make sure your FastAPI backend is running on port 8000!")
