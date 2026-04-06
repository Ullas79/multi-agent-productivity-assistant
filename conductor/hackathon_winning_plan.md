# AgentFlow - Hackathon Winning Implementation Plan

## Objective
Elevate the baseline AgentFlow project (which already meets all core requirements) into an enterprise-grade, highly impressive Multi-Agent System. The goal is to maximize the "wow" factor for the Gen AI Academy APAC Hackathon judges by demonstrating advanced Google Cloud capabilities, agent transparency, and enterprise security.

## Scope & Impact
The improvements will touch the database, backend agents, API endpoints, and the frontend UI.
1.  **Enterprise Security & AI**: Migrating from consumer Gemini API to Google Cloud Vertex AI.
2.  **Agent Transparency (UI/UX)**: Implementing "Thought Process" streaming to visualize agent orchestration in real-time.
3.  **Agentic Memory (RAG)**: Integrating AlloyDB `pgvector` for semantic search capabilities.
4.  **Resilience**: Adding a reflection/self-correction loop for agent tool failures.

## Implementation Steps

### Phase 1: Enterprise Foundation (Vertex AI Migration)
*Goal: Prove enterprise-readiness by using GCP IAM and Vertex AI instead of raw API keys.*
1.  **Update Dependencies**: Replace `google-generativeai` / `langchain-google-genai` with `google-cloud-aiplatform` / `langchain-google-vertexai` in `requirements.txt` or `pyproject.toml`.
2.  **Update Configuration**: Modify `backend/config.py` and `.env` to remove `GOOGLE_API_KEY` and add `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_REGION`.
3.  **Refactor Agent Initialization**: In `backend/agents/orchestrator.py` (and any other agent files), initialize the LLM using Vertex AI (`ChatVertexAI` or `GenerativeModel` with `vertexai.init`).
4.  **IAM Setup**: Ensure the local environment and Cloud Run service account have the `roles/aiplatform.user` role.

### Phase 2: The "Wow" Factor (Agent Transparency UI)
*Goal: Visually demonstrate the multi-agent orchestration happening under the hood.*
1.  **Backend Streaming Updates**: Modify the agent execution loop in `backend/agents/orchestrator.py` to yield intermediate steps (e.g., `{"type": "thought", "content": "Calling Calendar Agent..."}`).
2.  **Frontend SSE Handling**: Update `frontend/index.html` (or the relevant React component) to parse the new `"thought"` event types from the SSE stream.
3.  **UI Implementation**: Build a sleek, terminal-like UI component that displays the agent's thought process step-by-step above the final text response, complete with loading spinners and checkmarks.

### Phase 3: Agentic Memory (RAG with AlloyDB pgvector)
*Goal: Move beyond literal text search to true semantic understanding.*
1.  **Database Configuration**: Enable the `pgvector` extension in the AlloyDB instance.
2.  **Schema Update**: Add a vector column (e.g., `embedding`) to the `notes` table in `backend/database/models.py` and generate an Alembic migration.
3.  **Embedding Generation**: Update `backend/mcp_servers/notes_server.py` to call the Vertex AI text-embedding model when a new note is created or updated, and store the resulting vector.
4.  **Semantic Search Tool**: Implement a new MCP tool (or update the existing `search_notes` tool) to perform cosine similarity searches against the embeddings.

### Phase 4: Agentic Debate & Self-Correction (Stretch Goal)
*Goal: Show robust error handling and autonomous problem-solving.*
1.  **Prompt Engineering**: Update the Orchestrator's system prompt to mandate finding workarounds if a sub-agent's tool call fails (e.g., if a calendar slot is booked, ask the task agent if the conflicting task can be moved).
2.  **Error Interception**: Implement try/catch blocks within the agent execution loop to catch tool execution errors and feed them back to the LLM for reflection.

## Verification & Testing
- Verify Vertex AI integration by running the app without a `GOOGLE_API_KEY` environment variable.
- Test the UI streaming by triggering a multi-tool workflow (e.g., "Create a task and schedule a meeting for it") and observing the thought process UI.
- Validate semantic search by creating notes with synonyms and querying with different terminology.

## Migration & Rollback
- Create a new git branch for these experimental features (e.g., `feature/hackathon-winning-upgrades`).
- Apply database migrations incrementally. If `pgvector` causes issues locally, roll back the migration and focus on Phase 1 & 2 for the demo.