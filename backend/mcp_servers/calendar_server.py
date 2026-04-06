"""
backend/mcp_servers/calendar_server.py – MCP server for Calendar management.

Tools:
  - create_event: Schedule a new calendar event
  - list_events: List upcoming events with date filtering
  - check_availability: Check if a time slot is free
"""
import logging
from datetime import datetime, timedelta, timezone
from mcp.server import Server
import mcp.types as types
import backend.database.connection as db_conn
from backend.database import crud

logger = logging.getLogger(__name__)

calendar_server = Server("calendar_manager")


@calendar_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="create_event",
            description="Schedule a new calendar event.",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_name": {"type": "string", "description": "Patient's name"},
                    "doctor_name": {"type": "string", "description": "Doctor's name"},
                    "start_time": {"type": "string", "description": "Start time in ISO format"},
                    "end_time": {"type": "string", "description": "End time in ISO format"},
                    "reason": {"type": "string", "description": "Reason for appointment"},
                    "location": {"type": "string", "description": "Location or room"},
                },
                "required": ["patient_name", "doctor_name", "start_time", "end_time"],
            },
        ),
        types.Tool(
            name="list_events",
            description="List calendar events, optionally filtered by date range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_from": {"type": "string", "description": "Start of date range (ISO format)"},
                    "start_until": {"type": "string", "description": "End of date range (ISO format)"},
                    "limit": {"type": "integer", "description": "Max results (default 10)"},
                },
            },
        ),
        types.Tool(
            name="check_availability",
            description="Check if a time slot has any conflicting events.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_time": {"type": "string", "description": "Start of time window (ISO format)"},
                    "end_time": {"type": "string", "description": "End of time window (ISO format)"},
                },
                "required": ["start_time", "end_time"],
            },
        ),
    ]


@calendar_server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    if not arguments:
        arguments = {}

    if name == "create_event":
        async with db_conn.AsyncSessionLocal() as db:
            event = await crud.create_event(
                db,
                patient_name=arguments.get("patient_name", "Unknown"),
                doctor_name=arguments.get("doctor_name", "Unknown"),
                start_time=arguments.get("start_time"),
                end_time=arguments.get("end_time"),
                reason=arguments.get("reason", ""),
                location=arguments.get("location", ""),
            )
            await db.commit()
        return [types.TextContent(
            type="text",
            text=(
                f"Appointment scheduled: {event.patient_name} with Dr. {event.doctor_name}\n"
                f"  📅 {event.start_time.strftime('%Y-%m-%d %H:%M')} → {event.end_time.strftime('%H:%M')}\n"
                f"  📍 {event.location or 'No location'}\n"
                f"  ID: {event.id}"
            ),
        )]

    elif name == "list_events":
        start_from = arguments.get("start_from")
        start_until = arguments.get("start_until")
        # Default: show events from now to 7 days ahead
        if not start_from:
            start_from = datetime.now(timezone.utc).isoformat()
        if not start_until:
            start_until = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

        async with db_conn.AsyncSessionLocal() as db:
            events = await crud.get_events(
                db,
                start_from=start_from,
                start_until=start_until,
                limit=arguments.get("limit", 10),
            )
        if not events:
            return [types.TextContent(type="text", text="No upcoming events found in that time range.")]
        lines = [f"Found {len(events)} upcoming event(s):\n"]
        for i, e in enumerate(events, 1):
            lines.append(
                f"{i}. 📅 {e.patient_name} with Dr. {e.doctor_name}\n"
                f"   {e.start_time.strftime('%a %b %d, %H:%M')} → {e.end_time.strftime('%H:%M')}\n"
                f"   📍 {e.location or 'No location'}  ID:{e.id}"
            )
        return [types.TextContent(type="text", text="\n".join(lines))]

    elif name == "check_availability":
        start_time = arguments.get("start_time")
        end_time = arguments.get("end_time")
        if not start_time or not end_time:
            return [types.TextContent(type="text", text="Error: start_time and end_time are required.")]

        async with db_conn.AsyncSessionLocal() as db:
            # Find events overlapping with the requested window
            events = await crud.get_events(
                db, start_from=start_time, start_until=end_time, limit=50,
            )
        if not events:
            return [types.TextContent(
                type="text",
                text=f"✅ Time slot is AVAILABLE. No conflicts between {start_time} and {end_time}."
            )]
        lines = [f"⚠️ CONFLICT – {len(events)} event(s) overlap with that time slot:\n"]
        for e in events:
            lines.append(
                f"  - {e.patient_name} with Dr. {e.doctor_name} ({e.start_time.strftime('%H:%M')}–{e.end_time.strftime('%H:%M')})"
            )
        return [types.TextContent(type="text", text="\n".join(lines))]

    raise ValueError(f"Unknown tool: {name}")


async def main():
    import mcp.server.stdio
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await calendar_server.run(read_stream, write_stream, calendar_server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
