"""
backend/agents/orchestrator.py – Primary Orchestrator Agent.

Coordinates sub-agents (Task, Calendar, Notes) to handle user requests.
Each sub-agent calls real MCP tools that read/write the database.

Architecture:
  User → Orchestrator → Sub-Agent → MCP Tool → CRUD → Database
                ↘ saves conversation to Agent Memory
"""
import asyncio
import logging
from typing import AsyncGenerator, Union, Dict

from backend.agents import task_agent, calendar_agent, notes_agent

logger = logging.getLogger(__name__)

# Lazy-load the LLM
_llm = None


def _get_llm():
    global _llm
    if _llm is not None:
        return _llm
    try:
        import vertexai
        from langchain_google_vertexai import ChatVertexAI
        from backend.config import get_settings

        settings = get_settings()
        if not settings.google_cloud_project:
            logger.warning("No GCP project configured – LLM unavailable, using tool output directly.")
            return None
        vertexai.init(
            project=settings.google_cloud_project,
            location=settings.google_cloud_region,
        )
        _llm = ChatVertexAI(
            model_name=settings.gemini_model,
            project=settings.google_cloud_project,
            location=settings.google_cloud_region,
            temperature=0.2,
            streaming=True,
        )
    except Exception as e:
        logger.warning(f"Vertex AI LLM unavailable: {e}")
    return _llm


SYSTEM_INSTRUCTION = (
    "You are AgentFlow's Orchestrator – an enterprise AI coordinator. "
    "You manage three specialist sub-agents:\n"
    "  1. Task Agent – manages to-do items, priorities, and task tracking\n"
    "  2. Calendar Agent – handles scheduling, events, and availability checks\n"
    "  3. Notes Agent – manages notes and knowledge search\n\n"
    "When a user request spans multiple domains (e.g., 'create a task and schedule "
    "a meeting'), you coordinate between agents step by step.\n"
    "If conflicts arise, debate workarounds before giving up."
)


def _route_to_agent(message: str) -> list[str]:
    """
    Classify the user message and decide which sub-agent(s) to invoke.
    Returns a list because some requests span multiple agents.
    """
    msg = message.lower()
    agents = []

    # Task-related keywords
    if any(kw in msg for kw in [
        "task", "todo", "to-do", "to do", "assign", "priority",
        "complete", "finish", "checklist", "backlog",
    ]):
        agents.append("task")

    # Calendar-related keywords
    if any(kw in msg for kw in [
        "schedule", "calendar", "meeting", "event", "appointment",
        "available", "book", "slot", "reschedule",
    ]):
        agents.append("calendar")

    # Notes-related keywords
    if any(kw in msg for kw in [
        "note", "write down", "jot", "search", "find info",
        "knowledge", "remember", "look up", "document",
    ]):
        agents.append("notes")

    # If no specific domain detected, fall back to general
    if not agents:
        agents.append("general")

    return agents


async def _save_to_memory(session_id: str, role: str, content: str):
    """Persist conversation turn to agent memory (non-blocking)."""
    try:
        from backend.database.connection import AsyncSessionLocal, _ensure_engine
        from backend.database import crud
        _ensure_engine()
        async with AsyncSessionLocal() as db:
            await crud.save_memory(db, session_id, role, content, agent_name="orchestrator")
            await db.commit()
    except Exception as e:
        logger.debug(f"Failed to save memory (non-critical): {e}")


async def run_agent(
    user_message: str, session_id: str
) -> AsyncGenerator[Union[str, Dict[str, str]], None]:
    """
    Main entry point for the Orchestrator.
    Routes to sub-agents, which call MCP tools for real DB operations.
    """
    llm = _get_llm()

    # Save user message to memory
    asyncio.create_task(_save_to_memory(session_id, "user", user_message))

    # 1. Classify intent
    yield {"type": "thought", "content": "🧠 Orchestrator analyzing intent..."}
    target_agents = _route_to_agent(user_message)
    agent_names = ", ".join(a.title() + " Agent" for a in target_agents)
    yield {"type": "thought", "content": f"🔀 Routing to: {agent_names}"}
    await asyncio.sleep(0.3)

    collected_response = []

    # 2. Execute each sub-agent in sequence
    for agent_key in target_agents:
        if agent_key == "task":
            yield {"type": "thought", "content": "── Delegating to Task Agent ──"}
            async for event in task_agent.run(user_message, session_id, llm=llm):
                if isinstance(event, dict) and event.get("type") == "text":
                    collected_response.append(event.get("content", ""))
                yield event

        elif agent_key == "calendar":
            yield {"type": "thought", "content": "── Delegating to Calendar Agent ──"}
            async for event in calendar_agent.run(user_message, session_id, llm=llm):
                if isinstance(event, dict) and event.get("type") == "text":
                    collected_response.append(event.get("content", ""))
                yield event

        elif agent_key == "notes":
            yield {"type": "thought", "content": "── Delegating to Notes Agent ──"}
            async for event in notes_agent.run(user_message, session_id, llm=llm):
                if isinstance(event, dict) and event.get("type") == "text":
                    collected_response.append(event.get("content", ""))
                yield event

        elif agent_key == "general":
            yield {"type": "thought", "content": "── General Assistant Mode ──"}
            await asyncio.sleep(0.2)
            if llm:
                try:
                    context = (
                        f"System: {SYSTEM_INSTRUCTION}\n\n"
                        f"User: {user_message}\n\n"
                        f"Respond helpfully. If the request relates to tasks, calendar, "
                        f"or notes, suggest using specific commands."
                    )
                    response = await llm.ainvoke(context)
                    if response.content:
                        words = response.content.split(" ")
                        for i, word in enumerate(words):
                            chunk = word if i == 0 else " " + word
                            yield {"type": "text", "content": chunk}
                            collected_response.append(chunk)
                            await asyncio.sleep(0.02)
                except Exception as e:
                    logger.error(f"LLM error: {e}")
                    yield {
                        "type": "text",
                        "content": (
                            "I can help you with:\n"
                            "• **Tasks** – create, list, update, or complete tasks\n"
                            "• **Calendar** – schedule events, check availability\n"
                            "• **Notes** – create or search your notes\n\n"
                            "What would you like to do?"
                        ),
                    }
            else:
                yield {
                    "type": "text",
                    "content": (
                        "👋 I'm AgentFlow! I manage three specialist agents:\n\n"
                        "• **Task Agent** – \"show my tasks\", \"create a task: Review PR\"\n"
                        "• **Calendar Agent** – \"schedule a meeting tomorrow at 2pm\"\n"
                        "• **Notes Agent** – \"search notes about architecture\"\n\n"
                        "What can I help you with?"
                    ),
                }

    # Multi-agent separator
    if len(target_agents) > 1:
        yield {"type": "thought", "content": "🔗 All sub-agents completed – multi-domain request fulfilled."}

    # Save assistant response to memory
    full_response = "".join(collected_response)
    if full_response:
        asyncio.create_task(_save_to_memory(session_id, "assistant", full_response[:2000]))
