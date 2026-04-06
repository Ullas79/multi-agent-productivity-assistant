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
            name="create_clinical_task",
            description="Create a new clinical task for a patient.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title (e.g., Check Vitals)"},
                    "patient_name": {"type": "string", "description": "Name of the patient"},
                    "description": {"type": "string", "description": "Detailed medical description"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "due_date": {"type": "string", "description": "Due date in ISO format"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "patient_name"],
            },
        ),
        types.Tool(
            name="list_clinical_tasks",
            description="List clinical tasks.",
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
    
    if name == "create_clinical_task":
        async with db_conn.AsyncSessionLocal() as db:
            task = await crud.create_task(
                db,
                title=arguments.get("title"),
                patient_name=arguments.get("patient_name"),
                description=arguments.get("description", ""),
                priority=arguments.get("priority", "medium"),
                due_date=arguments.get("due_date"),
                tags=arguments.get("tags", []),
            )
            await db.commit()
        return [types.TextContent(type="text", text=f"Clinical Task created for {task.patient_name}: '{task.title}'")]

    elif name == "list_clinical_tasks":
        async with db_conn.AsyncSessionLocal() as db:
            tasks = await crud.get_tasks(db, status=arguments.get("status"), priority=arguments.get("priority"))
        if not tasks: return [types.TextContent(type="text", text="No tasks found.")]
        lines = [f"Found {len(tasks)} task(s):\n"]
        for t in tasks:
            lines.append(f"- [{t.status}] {t.title} for Patient: {t.patient_name} (Priority: {t.priority})")
        return [types.TextContent(type="text", text="\n".join(lines))]

    raise ValueError(f"Unknown tool: {name}")

async def main():
    import mcp.server.stdio
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await tasks_server.run(read_stream, write_stream, tasks_server.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
