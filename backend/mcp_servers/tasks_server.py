"""
backend/mcp_servers/tasks_server.py – MCP server for Clinical Task management.
"""
import logging
from mcp.server import Server
import mcp.types as types
import backend.database.connection as db_conn
from backend.database import crud

logger = logging.getLogger(__name__)
tasks_server = Server("task_manager")

@tasks_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="create_task",
            description="Create a new task in the productivity hub.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title (e.g., Prepare Presentation)"},
                    "owner": {"type": "string", "description": "Who this task is for (defaults to user)"},
                    "description": {"type": "string", "description": "Detailed task description"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "due_date": {"type": "string", "description": "Due date in ISO format"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title"],
            },
        ),
        types.Tool(
            name="list_tasks",
            description="List and filter tasks in the productivity hub.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["todo", "in_progress", "done"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                },
            },
        )
    ]

@tasks_server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    arguments = arguments or {}
    
    if name == "create_task":
        async with db_conn.AsyncSessionLocal() as db:
            task = await crud.create_task(
                db,
                title=arguments.get("title"),
                patient_name=arguments.get("owner", "user"),
                description=arguments.get("description", ""),
                priority=arguments.get("priority", "medium"),
                due_date=arguments.get("due_date"),
                tags=arguments.get("tags", []),
            )
            await db.commit()
        return [types.TextContent(type="text", text=f"Task '{task.title}' created successfully.")]

    elif name == "list_tasks":
        async with db_conn.AsyncSessionLocal() as db:
            tasks = await crud.get_tasks(db, status=arguments.get("status"), priority=arguments.get("priority"))
        if not tasks: return [types.TextContent(type="text", text="No tasks found.")]
        lines = [f"Found {len(tasks)} task(s):\n"]
        for t in tasks:
            lines.append(f"- [{t.status}] {t.title} (Owner: {t.patient_name}, Priority: {t.priority})")
        return [types.TextContent(type="text", text="\n".join(lines))]

    raise ValueError(f"Unknown tool: {name}")

async def main():
    import mcp.server.stdio
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await tasks_server.run(read_stream, write_stream, tasks_server.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
