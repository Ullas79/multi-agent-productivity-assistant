"""
backend/agents/calendar_agent.py – Calendar Management Sub-Agent.

Handles scheduling, availability checks, and event listing
by calling Calendar MCP tools with real database operations.
"""
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Union, Dict

from backend.mcp_servers.calendar_server import handle_call_tool as calendar_tool
from backend.agents.base import stream_llm_response

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are a Calendar & Scheduling specialist agent. You help users "
    "schedule meetings, check availability, and manage their calendar. "
    "You have access to: create_event, list_events, check_availability. "
    "When scheduling conflicts arise, propose alternatives. "
    "Always base your response on the actual tool results provided."
)


def _parse_datetime_hint(message: str) -> dict:
    """Extract date/time hints from natural language."""
    msg = message.lower()
    now = datetime.now(timezone.utc)
    hints = {}

    if "tomorrow" in msg:
        target = now + timedelta(days=1)
        hints["date"] = target.strftime("%Y-%m-%d")
    elif "today" in msg:
        hints["date"] = now.strftime("%Y-%m-%d")
    elif "next week" in msg:
        target = now + timedelta(days=7)
        hints["date"] = target.strftime("%Y-%m-%d")

    # Try to find time patterns like "2pm", "14:00", "3:30pm"
    time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', msg)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        ampm = time_match.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        hints["hour"] = hour
        hints["minute"] = minute

    return hints


def _classify_calendar_intent(message: str) -> tuple[str, dict]:
    """Determine which MCP tool to call and extract parameters."""
    msg = message.lower()
    time_hints = _parse_datetime_hint(message)

    # Check availability
    if any(word in msg for word in ["available", "free", "busy", "conflict", "open slot"]):
        date = time_hints.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        hour = time_hints.get("hour", 9)
        minute = time_hints.get("minute", 0)
        start = f"{date}T{hour:02d}:{minute:02d}:00"
        end = f"{date}T{hour + 1:02d}:{minute:02d}:00"
        return "check_availability", {"start_time": start, "end_time": end}

    # Create event / schedule
    if any(word in msg for word in ["schedule", "book", "create", "set up", "arrange"]):
        # Extract title
        title = message
        for prefix in ["schedule a", "schedule", "book a", "book", "create an event",
                        "create event", "set up a", "set up", "arrange a", "arrange"]:
            if msg.startswith(prefix):
                title = message[len(prefix):].strip().strip(":").strip()
                break

        date = time_hints.get("date", (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d"))
        hour = time_hints.get("hour", 10)
        minute = time_hints.get("minute", 0)
        start = f"{date}T{hour:02d}:{minute:02d}:00"
        end_hour = hour + 1
        end = f"{date}T{end_hour:02d}:{minute:02d}:00"

        return "create_with_check", {
            "title": title or "New Meeting",
            "start_time": start,
            "end_time": end,
            "description": "",
            "location": "",
        }

    # List / show events
    return "list_events", {}


async def run(
    user_message: str, session_id: str, llm=None
) -> AsyncGenerator[Union[str, Dict[str, str]], None]:
    """Execute the calendar agent – calls real MCP tools."""

    yield {"type": "thought", "content": "📅 Calendar Agent activated – analyzing request..."}

    tool_name, tool_args = _classify_calendar_intent(user_message)

    if tool_name == "create_with_check":
        # Multi-step workflow: check availability FIRST, then create
        yield {"type": "thought", "content": f"🔍 Checking availability for {tool_args['start_time']}..."}

        avail_results = await calendar_tool("check_availability", {
            "start_time": tool_args["start_time"],
            "end_time": tool_args["end_time"],
        })
        avail_output = avail_results[0].text if avail_results else "No output"

        if "CONFLICT" in avail_output:
            yield {"type": "thought", "content": "⚠️ Schedule conflict detected!"}
            yield {"type": "thought", "content": "🔄 Proposing alternative time slot..."}
            tool_output = avail_output + "\n\nI'll suggest an alternative time."
        else:
            yield {"type": "thought", "content": "✅ Time slot is clear – creating event..."}
            create_results = await calendar_tool("create_event", tool_args)
            create_out = create_results[0].text if create_results else "No output"
            tool_output = f"Availability: {avail_output}\n\n{create_out}"
            yield {"type": "thought", "content": "✅ Event created successfully!"}

    else:
        yield {"type": "thought", "content": f"🔧 Calling MCP tool: {tool_name}"}
        results = await calendar_tool(tool_name, tool_args)
        tool_output = results[0].text if results else "No output"
        yield {"type": "thought", "content": "✅ Calendar data retrieved."}

    # Use shared LLM streaming utility
    async for event in stream_llm_response(
        llm, SYSTEM_PROMPT, user_message, tool_name, tool_output, tool_output
    ):
        yield event
