"""
backend/mcp_servers/notes_server.py – MCP server for Notes management.
"""
import logging
from mcp.server import Server
import mcp.types as types
import backend.database.connection as db_conn
from backend.database import crud

logger = logging.getLogger(__name__)

notes_server = Server("notes_manager")


@notes_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="create_note",
            description="Create a new note with automatic semantic embedding.",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_name": {"type": "string", "description": "The name of the patient"},
                    "content": {"type": "string", "description": "The full text content"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags"},
                },
                "required": ["patient_name", "content"],
            },
        ),
        types.Tool(
            name="semantic_search",
            description="AI-powered semantic search across all notes using pgvector.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The concept or topic to search for"},
                    "limit": {"type": "integer", "description": "Number of results (default 3)"},
                },
                "required": ["query"],
            },
        ),
    ]


@notes_server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    if not arguments:
        arguments = {}

    if name == "semantic_search":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 3)
        async with db_conn.AsyncSessionLocal() as db:
            results = await crud.semantic_search_notes(db, query, limit=limit)
        if not results:
            return [types.TextContent(type="text", text="No semantically similar notes found.")]
        output = f"Top {len(results)} most relevant notes:\n\n"
        for i, note in enumerate(results, 1):
            preview = note.content[:500]
            output += f"{i}. Patient: {note.patient_name}\n{preview}...\n\n"
        return [types.TextContent(type="text", text=output)]

    elif name == "create_note":
        patient_name = arguments.get("patient_name", "Unknown")
        content = arguments.get("content", "")
        tags = arguments.get("tags", [])
        async with db_conn.AsyncSessionLocal() as db:
            await crud.create_note(db, patient_name, content, tags)
            await db.commit()
        return [types.TextContent(type="text", text=f"Record for '{patient_name}' created successfully.")]

    raise ValueError(f"Unknown tool: {name}")


async def main():
    import mcp.server.stdio
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await notes_server.run(read_stream, write_stream, notes_server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())