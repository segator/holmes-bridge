"""HolmesGPT API client."""

import logging
from typing import Any

import httpx

from app.config import HOLMES_API_URL, HOLMES_MODEL

logger = logging.getLogger(__name__)

# Generous timeout — LLM calls can take 30-60s
_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)


async def investigate(
    title: str,
    description: str,
    subject: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send an investigation request to HolmesGPT.

    Uses POST /api/investigate for structured alert investigation.
    """
    payload: dict[str, Any] = {
        "source": "grafana",
        "title": title,
        "description": description,
        "model": HOLMES_MODEL,
        "include_tool_calls": True,
    }
    if subject:
        payload["subject"] = subject
    if context:
        payload["context"] = context

    logger.info("Investigating: %s", title)
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(f"{HOLMES_API_URL}/api/investigate", json=payload)
        resp.raise_for_status()
        return resp.json()


async def chat(
    question: str, conversation_history: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    """Send a freeform question to HolmesGPT.

    Uses POST /api/chat for interactive Telegram /ask commands.
    """
    payload: dict[str, Any] = {
        "ask": question,
        "model": HOLMES_MODEL,
    }
    if conversation_history:
        payload["conversation_history"] = conversation_history

    logger.info("Chat question: %s", question[:100])
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(f"{HOLMES_API_URL}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()
