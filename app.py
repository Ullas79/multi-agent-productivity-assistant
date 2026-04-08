# app.py - Run with: streamlit run app.py
import json
import uuid

import requests
import streamlit as st

# Configuration
API_URL = "http://127.0.0.1:8000/api/chat"

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
                    buffer = ""
                    done = False
                    saw_error = False

                    for chunk in r.iter_content(chunk_size=None):
                        if not chunk:
                            continue

                        buffer += chunk.decode("utf-8", errors="ignore")

                        # SSE events are separated by a blank line
                        while "\n\n" in buffer:
                            event, buffer = buffer.split("\n\n", 1)

                            for line in event.splitlines():
                                if not line.startswith("data: "):
                                    continue

                                payload = line[6:].strip()
                                if not payload:
                                    continue

                                try:
                                    data = json.loads(payload)
                                except json.JSONDecodeError:
                                    continue

                                event_type = data.get("type")

                                if event_type == "text":
                                    full_response += data.get("content", "")
                                    message_placeholder.markdown(full_response + "▌")

                                elif event_type == "session_id" and data.get(
                                    "session_id"
                                ):
                                    st.session_state.session_id = data["session_id"]

                                elif event_type == "error":
                                    saw_error = True
                                    full_response += (
                                        f"\n\n⚠️ {data.get('content', 'Unknown error')}"
                                    )

                                elif event_type == "done":
                                    done = True
                                    break

                            if done:
                                break

                        if done:
                            break

                status.update(
                    label="Workflow Complete!", state="complete", expanded=False
                )

                if not full_response.strip() and not saw_error:
                    full_response = "No response received from orchestrator."

                message_placeholder.markdown(full_response)
                st.session_state.messages.append(
                    {"role": "assistant", "content": full_response}
                )

            except Exception:
                status.update(label="API Error", state="error")
                st.error("Make sure your FastAPI backend is running on port 8000!")
