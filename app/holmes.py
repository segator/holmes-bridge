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
    """Send an investigation request to HolmesGPT via /api/chat.

    Holmes 0.24.0 removed /api/investigate. We compose a prompt from
    the alert details and use /api/chat instead.
    """
    # Build a rich prompt from the alert details
    prompt_parts = [
        f"Investigate this Grafana alert:",
        f"Alert: {title}",
    ]
    if description:
        prompt_parts.append(f"Details: {description}")
    if context and context.get("labels"):
        labels = context["labels"]
        labels_str = ", ".join(f"{k}={v}" for k, v in labels.items())
        prompt_parts.append(f"Labels: {labels_str}")

    prompt_parts.append(
        "Investigate the root cause, check relevant pods/logs/metrics, "
        "and suggest a fix if possible."
    )

    return await chat("\n".join(prompt_parts))


async def chat(
    question: str, conversation_history: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    """Send a freeform question to HolmesGPT.

    Uses POST /api/chat (the only endpoint in Holmes 0.24.0+).
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
