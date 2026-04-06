"""
backend/agents/notes_agent.py – Notes & Knowledge Management Sub-Agent.

Handles note creation, search, and retrieval by calling Notes MCP tools.
"""
import logging
from typing import AsyncGenerator, Union, Dict

from backend.mcp_servers.notes_server import handle_call_tool as notes_tool
from backend.agents.base import stream_llm_response

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are a Notes & Knowledge Management specialist agent. You help users "
    "create, search, and organise their notes and knowledge base. "
    "You have access to: create_note, semantic_search. "
    "When searching, always present the most relevant results with context. "
    "Base your response on the actual tool results provided."
)


def _classify_notes_intent(message: str) -> tuple[str, dict]:
    """Determine which MCP tool to call and extract parameters."""
    msg = message.lower()

    # Create / write / save a note
    if any(word in msg for word in ["create", "write", "save", "add", "new note", "jot down"]):
        title = message
        for prefix in ["create a note", "create note", "write a note", "write note",
                        "save a note", "save note", "add a note", "add note",
                        "jot down", "note down"]:
            if msg.startswith(prefix):
                title = message[len(prefix):].strip().strip(":").strip()
                break
        # Split title from content at first sentence boundary
        parts = title.split(".", 1)
        note_title = parts[0].strip() or "Untitled Note"
        note_content = parts[1].strip() if len(parts) > 1 else title
        return "create_note", {
            "title": note_title[:100],
            "content": note_content,
            "tags": [],
        }

    # Search / find / look up
    if any(word in msg for word in ["search", "find", "look", "about", "related", "what do"]):
        # Extract query: strip common prefixes
        query = message
        for prefix in ["search for", "search notes for", "search notes about",
                        "find notes about", "find notes on", "look for", "look up",
                        "search", "find"]:
            if msg.startswith(prefix):
                query = message[len(prefix):].strip()
                break
        return "semantic_search", {"query": query, "limit": 5}

    # Default: search for what they mentioned
    return "semantic_search", {"query": message, "limit": 5}


async def run(
    user_message: str, session_id: str, llm=None
) -> AsyncGenerator[Union[str, Dict[str, str]], None]:
    """Execute the notes agent – calls real MCP tools."""

    yield {"type": "thought", "content": "🗒️ Notes Agent activated – analyzing request..."}

    tool_name, tool_args = _classify_notes_intent(user_message)

    yield {"type": "thought", "content": f"🔧 Calling MCP tool: {tool_name}"}

    results = await notes_tool(tool_name, tool_args)
    tool_output = results[0].text

    if tool_name == "create_note":
        yield {"type": "thought", "content": "✅ Note saved to database."}
    else:
        yield {"type": "thought", "content": "🔍 Semantic search complete – ranking results..."}

    # Use shared LLM streaming utility
    async for event in stream_llm_response(
        llm, SYSTEM_PROMPT, user_message, tool_name, tool_output, tool_output
    ):
        yield event
