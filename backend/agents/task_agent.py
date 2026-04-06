"""
backend/agents/task_agent.py – Task Management Sub-Agent.

Handles user requests related to tasks by calling Task MCP tools.
Returns real data from the database, not fabricated responses.
"""
import logging
from typing import AsyncGenerator, Union, Dict

from backend.mcp_servers.tasks_server import handle_call_tool as tasks_tool
from backend.agents.base import stream_llm_response

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are a Task Management specialist agent. You help users create, "
    "organise, and track their clinical tasks. You have access to the following "
    "tools: create_clinical_task, list_clinical_tasks, update_task, complete_task. "
    "Always respond based on the actual tool results provided. "
    "Be concise and action-oriented."
)


def _classify_task_intent(message: str) -> tuple[str, dict]:
    """Determine which MCP tool to call and extract parameters."""
    msg = message.lower()

    # Complete / finish / done
    if any(word in msg for word in ["complete", "finish", "done", "mark"]):
        return "list_then_respond", {"intent": "complete"}

    # Create / add / new
    if any(word in msg for word in ["create", "add", "new", "make"]):
        # Extract title: everything after the action word
        title = message
        for prefix in ["create a task", "create task", "add a task", "add task",
                        "new task", "make a task", "create a", "add a", "add"]:
            if msg.startswith(prefix):
                title = message[len(prefix):].strip().strip(":").strip()
                break
        priority = "high" if "urgent" in msg or "important" in msg else "medium"
        if "low" in msg:
            priority = "low"
        return "create_clinical_task", {
            "title": title or "New Task",
            "patient_name": "Unknown Patient", # Placeholder if none extracted easily
            "priority": priority,
            "description": "",
        }

    # List / show / what
    if any(word in msg for word in ["list", "show", "what", "all", "pending", "my task", "get"]):
        status = None
        if "todo" in msg or "pending" in msg or "open" in msg:
            status = "todo"
        elif "progress" in msg or "working" in msg:
            status = "in_progress"
        elif "done" in msg or "completed" in msg or "finished" in msg:
            status = "done"
        priority = None
        if "high" in msg:
            priority = "high"
        elif "low" in msg:
            priority = "low"
        return "list_clinical_tasks", {"status": status, "priority": priority, "limit": 10}

    # Default: list tasks and let LLM reason
    return "list_clinical_tasks", {"limit": 10}


async def run(
    user_message: str, session_id: str, llm=None
) -> AsyncGenerator[Union[str, Dict[str, str]], None]:
    """Execute the task agent – calls real MCP tools and returns real data."""

    yield {"type": "thought", "content": "📝 Task Agent activated – analyzing request..."}

    tool_name, tool_args = _classify_task_intent(user_message)
    clean_args = {k: v for k, v in tool_args.items() if v is not None and k != "intent"}

    if tool_name == "list_then_respond":
        # For complete/update: first list tasks so user can see them
        yield {"type": "thought", "content": "📋 Fetching current tasks from database..."}
        results = await tasks_tool("list_clinical_tasks", {"limit": 10, "status": "todo"})
        tool_output = results[0].text
        yield {"type": "thought", "content": "✅ Tasks retrieved – preparing response..."}
    else:
        yield {"type": "thought", "content": f"🔧 Calling MCP tool: {tool_name}({clean_args})"}
        results = await tasks_tool(tool_name, clean_args)
        tool_output = results[0].text
        yield {"type": "thought", "content": "✅ Tool execution complete – formatting response..."}

    # Use shared LLM streaming utility
    async for event in stream_llm_response(
        llm, SYSTEM_PROMPT, user_message, tool_name, tool_output, tool_output
    ):
        yield event
