"""
backend/agents/orchestrator.py - The Hospital Routing Agent

This module keeps Gemini client initialization lazy so importing the app
does not fail when API credentials are unavailable at import time.
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


SYSTEM_PROMPT = """You are the Lead Orchestrator Agent for an AI Hospital Management System.
Your job is to assist doctors and nurses by managing clinical tasks, scheduling appointments, and retrieving Patient Records (EHR).
You have access to medical tools. When a user makes a request, determine if you need to fetch data from the database or insert new data.
Always be highly professional, accurate, and concise. Do not guess patient data—if you don't know, say so."""


async def run_agent(message: str, session_id: str):
    """
    Async generator that streams the Gemini response back to the client.
    In a full ADK setup, this routes to sub-agents. For the hackathon demo,
    we simulate the multi-agent orchestration by handling the core logic here.
    """
    try:
        client = _get_client()

        # 1. Fetch conversation history from AlloyDB
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

        # 2. Call Gemini
        response = client.models.generate_content_stream(
            model=settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,  # Keep it strict for medical
            ),
        )

        # 3. Stream the response back to caller
        for chunk in response:
            if chunk.text:
                yield chunk.text

    except Exception as e:
        logger.exception("Orchestrator Error: %s", str(e))
        yield f"Error processing hospital request: {str(e)}"
