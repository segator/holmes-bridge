"""Telegram notification sender and bot command handler."""

import html
import logging
from typing import Any

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from app.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    GRAFANA_URL,
    ALLOWED_CHAT_IDS,
)
from app import holmes

logger = logging.getLogger(__name__)

# Max Telegram message length (HTML)
MAX_MSG_LEN = 4096

# The bot_app (created in create_bot_app) is the single source of truth.
# We store a reference here so send_message can use the same Bot instance
# that the Application's updater uses for polling, avoiding 409 conflicts.
_bot_app: Application | None = None


def _truncate(text: str, max_len: int = MAX_MSG_LEN) -> str:
    """Truncate text to fit Telegram's message limit."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 20] + "\n\n<i>[truncated]</i>"


def format_investigation(alert_title: str, result: dict[str, Any]) -> str:
    """Format a HolmesGPT investigation result for Telegram (HTML).

    Holmes 0.24.0 /api/chat returns {"analysis": "...", "conversation_history": [...]}.
    """
    analysis = result.get("analysis", "No analysis available.")

    parts = [
        f"<b>AI Investigation</b>",
        f"<b>Alert:</b> {html.escape(alert_title)}",
        "",
        f"{html.escape(analysis)}",
    ]

    return _truncate("\n".join(parts))


def format_chat_response(question: str, result: dict[str, Any]) -> str:
    """Format a HolmesGPT chat response for Telegram (HTML)."""
    answer = result.get("analysis") or result.get("response") or "No response."

    parts = [
        f"<b>Q:</b> {html.escape(question[:200])}",
        "",
        f"{html.escape(answer)}",
    ]

    return _truncate("\n".join(parts))


async def send_message(text: str, parse_mode: str = ParseMode.HTML) -> None:
    """Send a message to the configured Telegram chat.

    Uses the Application's bot instance (shared with the polling updater)
    to avoid creating multiple HTTP sessions to the Telegram API.
    """
    if _bot_app is None:
        logger.error("Bot app not initialized, cannot send message")
        return
    try:
        await _bot_app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode=parse_mode,
            disable_web_page_preview=True,
        )
    except Exception:
        logger.exception("Failed to send Telegram message")


async def send_investigation_result(alert_title: str, result: dict[str, Any]) -> None:
    """Format and send an investigation result to Telegram."""
    text = format_investigation(alert_title, result)
    await send_message(text)


async def handle_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ask command handler — send a question to HolmesGPT."""
    if update.effective_chat.id not in ALLOWED_CHAT_IDS:
        logger.warning("Unauthorized /ask from chat %s", update.effective_chat.id)
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /ask <question about the cluster>",
            parse_mode=ParseMode.HTML,
        )
        return

    question = " ".join(context.args)
    await update.message.reply_text("Investigating...", parse_mode=ParseMode.HTML)

    try:
        result = await holmes.chat(question)
        text = format_chat_response(question, result)
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    except Exception:
        logger.exception("Holmes chat failed for question: %s", question)
        await update.message.reply_text(
            "Investigation failed. Check bridge logs.",
            parse_mode=ParseMode.HTML,
        )


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help command handler."""
    if update.effective_chat.id not in ALLOWED_CHAT_IDS:
        logger.warning("Unauthorized /help from chat %s", update.effective_chat.id)
        return
    text = (
        "<b>Holmes Bridge Commands</b>\n\n"
        "/ask &lt;question&gt; — Ask the AI about the cluster\n"
        "/help — Show this help message"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


def create_bot_app() -> Application:
    """Create and configure the Telegram bot application.

    Uses a single httpx connection pool for both polling and sending.
    Configures timeouts to avoid overlapping getUpdates requests (409 Conflict).
    """
    global _bot_app
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .read_timeout(30)
        .connect_timeout(10)
        .pool_timeout(10)
        .build()
    )
    app.add_handler(CommandHandler("ask", handle_ask))
    app.add_handler(CommandHandler("help", handle_help))
    _bot_app = app
    return app
