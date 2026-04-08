"""
backend/agents/orchestrator.py - AgentFlow Orchestrator

This module manages the primary routing logic across specialised sub-agents.
It uses Google Gen AI SDK for high-performance streaming.
"""

import logging
from typing import Optional

from google import genai
from google.genai import types

from backend.config import get_settings
from backend.database import crud
from backend.database.connection import get_session_factory

logger = logging.getLogger(__name__)
settings = get_settings()

# Lazily initialized Gemini client (created only when first needed)
_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    """Return a lazily initialized Gemini client."""
    global _client
    if _client is not None:
        return _client

    # Prefer Vertex AI auth in GCP environments
    if settings.google_cloud_project:
        _client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_region,
        )
        return _client

    # Fall back to API key if provided
    if settings.google_api_key:
        _client = genai.Client(api_key=settings.google_api_key)
        return _client

    # Don't fail at import time; fail only when agent is actually invoked
    raise RuntimeError(
        "Gemini client is not configured. Set GOOGLE_API_KEY or configure "
        "GOOGLE_CLOUD_PROJECT with Vertex AI credentials."
    )


SYSTEM_PROMPT = """You are the Lead Orchestrator Agent for AgentFlow – a Multi-Agent AI Productivity Hub.
Your job is to assist users by coordinating specialised agents for Task Management, Calendar scheduling, and Notes/Knowledge retrieval.
You have access to powerful tools via sub-agents. When a user makes a request, route it to the appropriate sub-agent or respond directly if it's a general inquiry.
Always be professional, concise, and proactive. If a request involving multiple tools (e.g., 'Schedule a meeting and create a task') comes in, handle it step-by-step."""


async def run_agent(message: str, session_id: str):
    """
    Async generator that streams the Gemini response back to the client.
    In a full ADK setup, this routes to sub-agents. For the hackathon demo,
    we simulate the multi-agent orchestration by handling the core logic here.
    """
    try:
        client = _get_client()

        # Simple wrapper to match Langchain's async ainvoke signature for base.py
        class GeminiLLMWrapper:
            def __init__(self, c, m):
                self.client = c
                self.model = m
            async def ainvoke(self, context: str):
                class Response:
                    content = None
                resp = self.client.models.generate_content(
                    model=self.model,
                    contents=context,
                    config=types.GenerateContentConfig(temperature=0.2)
                )
                Response.content = resp.text
                return Response

        llm_wrapper = GeminiLLMWrapper(client, settings.gemini_model)
        msg_l = message.lower()

        # 1. Routing to sub-agents based on intent
        if any(k in msg_l for k in ["appointment", "schedule", "calendar", "book", "available", "conflict"]):
            from backend.agents.calendar_agent import run as run_cal
            async for chunk in run_cal(message, session_id, llm=llm_wrapper):
                yield chunk
            return
            
        elif any(k in msg_l for k in ["task", "todo", "complete", "finish", "done"]):
            from backend.agents.task_agent import run as run_task
            async for chunk in run_task(message, session_id, llm=llm_wrapper):
                yield chunk
            return
            
        elif any(k in msg_l for k in ["note", "record", "patient", "ehr", "search", "pull up"]):
            from backend.agents.notes_agent import run as run_notes
            async for chunk in run_notes(message, session_id, llm=llm_wrapper):
                yield chunk
            return

        # 2. Default behavior for general chat (no tools needed)
        # Fetch conversation history from AlloyDB
        AsyncSessionLocal = get_session_factory()
        async with AsyncSessionLocal() as db:
            history = await crud.get_memory(db, session_id)

        contents = []
        for mem in history[-5:]:  # Keep last 5 turns for context
            role = "user" if mem.role == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=mem.content)],
                )
            )

        # Add the new user message
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=message)],
            )
        )

        # Call Gemini
        response = client.models.generate_content_stream(
            model=settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,  # Keep it strict for medical
            ),
        )

        # Stream the response back to caller
        for chunk in response:
            if chunk.text:
                yield chunk.text

    except Exception as e:
        logger.exception("Orchestrator Error: %s", str(e))
        yield f"Error processing hospital request: {str(e)}"
