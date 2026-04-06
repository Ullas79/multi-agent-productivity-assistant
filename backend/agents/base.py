"""
backend/agents/base.py – Shared utilities for all sub-agents.

Eliminates duplicated LLM streaming and response formatting code
across task_agent, calendar_agent, and notes_agent.
"""
import logging
from typing import AsyncGenerator, Union, Dict, Optional

logger = logging.getLogger(__name__)

# Configurable streaming delay – set to 0 for Cloud Run production
STREAM_CHUNK_SIZE = 8  # words per chunk (reduces SSE overhead)


async def stream_llm_response(
    llm,
    system_prompt: str,
    user_message: str,
    tool_name: str,
    tool_output: str,
    fallback_output: str,
) -> AsyncGenerator[Union[str, Dict[str, str]], None]:
    """
    Shared LLM response streaming used by all sub-agents.

    If LLM is available, invokes it with context and streams the response
    in chunks. Falls back to raw tool output if LLM is unavailable or fails.

    Args:
        llm: The LangChain LLM instance (or None).
        system_prompt: The agent's system instruction.
        user_message: The user's original message.
        tool_name: Name of the MCP tool that was called.
        tool_output: Raw text output from the MCP tool.
        fallback_output: Text to yield if LLM is unavailable.
    """
    if llm:
        context = (
            f"System: {system_prompt}\n\n"
            f"User request: {user_message}\n\n"
            f"Tool '{tool_name}' returned:\n{tool_output}\n\n"
            f"Respond naturally based on the actual data. Be helpful and concise."
        )
        try:
            response = await llm.ainvoke(context)
            if response.content:
                words = response.content.split(" ")
                # Stream in chunks instead of word-by-word to reduce latency
                for i in range(0, len(words), STREAM_CHUNK_SIZE):
                    chunk_words = words[i:i + STREAM_CHUNK_SIZE]
                    chunk = " ".join(chunk_words)
                    if i > 0:
                        chunk = " " + chunk
                    yield {"type": "text", "content": chunk}
                return
        except Exception as e:
            logger.warning("LLM call failed, using raw tool output: %s", e)

    yield {"type": "text", "content": fallback_output}
