"""
backend/mcp_servers/tasks_server.py – MCP server for Task management.

Tools:
  - create_task: Create a new task
  - list_tasks: List tasks with optional filters
  - update_task: Update task properties
  - complete_task: Mark a task as done
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
            description="Create a new task in the task management system.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "description": {"type": "string", "description": "Detailed description"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"], "description": "Task priority"},
                    "due_date": {"type": "string", "description": "Due date in ISO format"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorisation"},
                },
                "required": ["title"],
            },
        ),
        types.Tool(
            name="list_tasks",
            description="List tasks with optional filtering by status and priority.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["todo", "in_progress", "done"], "description": "Filter by status"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"], "description": "Filter by priority"},
                    "limit": {"type": "integer", "description": "Max results (default 10)"},
                },
            },
        ),
        types.Tool(
            name="update_task",
            description="Update an existing task's properties (title, status, priority, etc.).",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "The task ID to update"},
                    "title": {"type": "string", "description": "New title"},
                    "status": {"type": "string", "enum": ["todo", "in_progress", "done"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "description": {"type": "string"},
                },
                "required": ["task_id"],
            },
        ),
        types.Tool(
            name="complete_task",
            description="Mark a task as done/completed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "The task ID to complete"},
                },
                "required": ["task_id"],
            },
        ),
    ]


@tasks_server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    if not arguments:
        arguments = {}

    if name == "create_task":
        async with db_conn.AsyncSessionLocal() as db:
            task = await crud.create_task(
                db,
                title=arguments.get("title", "Untitled"),
                description=arguments.get("description", ""),
                priority=arguments.get("priority", "medium"),
                due_date=arguments.get("due_date"),
                tags=arguments.get("tags", []),
            )
            await db.commit()
        return [types.TextContent(
            type="text",
            text=f"Task created: '{task.title}' (ID: {task.id}, Priority: {task.priority})"
        )]

    elif name == "list_tasks":
        async with db_conn.AsyncSessionLocal() as db:
            tasks = await crud.get_tasks(
                db,
                status=arguments.get("status"),
                priority=arguments.get("priority"),
                limit=arguments.get("limit", 10),
            )
        if not tasks:
            return [types.TextContent(type="text", text="No tasks found matching the criteria.")]
        lines = [f"Found {len(tasks)} task(s):\n"]
        for i, t in enumerate(tasks, 1):
            status_icon = {"todo": "⬜", "in_progress": "🔄", "done": "✅"}.get(t.status, "❓")
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t.priority, "⚪")
            due = f" (due: {t.due_date.strftime('%Y-%m-%d')})" if t.due_date else ""
            lines.append(f"{i}. {status_icon} {priority_icon} {t.title} [{t.status}]{due}  ID:{t.id}")
        return [types.TextContent(type="text", text="\n".join(lines))]

    elif name == "update_task":
        task_id = arguments.pop("task_id", None)
        if not task_id:
            return [types.TextContent(type="text", text="Error: task_id is required.")]
        async with db_conn.AsyncSessionLocal() as db:
            task = await crud.update_task(db, task_id, **arguments)
            await db.commit()
        if not task:
            return [types.TextContent(type="text", text=f"Error: Task {task_id} not found.")]
        return [types.TextContent(
            type="text",
            text=f"Task updated: '{task.title}' → status={task.status}, priority={task.priority}"
        )]

    elif name == "complete_task":
        task_id = arguments.get("task_id")
        if not task_id:
            return [types.TextContent(type="text", text="Error: task_id is required.")]
        async with db_conn.AsyncSessionLocal() as db:
            task = await crud.update_task(db, task_id, status="done")
            await db.commit()
        if not task:
            return [types.TextContent(type="text", text=f"Error: Task {task_id} not found.")]
        return [types.TextContent(type="text", text=f"Task '{task.title}' marked as ✅ done.")]

    raise ValueError(f"Unknown tool: {name}")


async def main():
    import mcp.server.stdio
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await tasks_server.run(read_stream, write_stream, tasks_server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
