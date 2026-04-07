"""Telegram notification sender and bot command handler."""

import html
import logging
from typing import Any

from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from app.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GRAFANA_URL
from app import holmes

logger = logging.getLogger(__name__)

# Max Telegram message length (HTML)
MAX_MSG_LEN = 4096

bot = Bot(token=TELEGRAM_BOT_TOKEN)


def _truncate(text: str, max_len: int = MAX_MSG_LEN) -> str:
    """Truncate text to fit Telegram's message limit."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 20] + "\n\n<i>[truncated]</i>"


def format_investigation(alert_title: str, result: dict[str, Any]) -> str:
    """Format a HolmesGPT investigation result for Telegram (HTML)."""
    analysis = result.get("analysis", "No analysis available.")
    tool_calls = result.get("tool_calls", [])

    parts = [
        f"<b>AI Investigation</b>",
        f"<b>Alert:</b> {html.escape(alert_title)}",
        "",
        f"{html.escape(analysis)}",
    ]

    if tool_calls:
        tools_used = set()
        for tc in tool_calls:
            tool_name = tc.get("tool_name") or tc.get("function", {}).get(
                "name", "unknown"
            )
            tools_used.add(tool_name)
        if tools_used:
            parts.append("")
            parts.append(f"<b>Tools used:</b> {', '.join(sorted(tools_used))}")

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
    """Send a message to the configured Telegram chat."""
    try:
        await bot.send_message(
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
    text = (
        "<b>Holmes Bridge Commands</b>\n\n"
        "/ask &lt;question&gt; — Ask the AI about the cluster\n"
        "/help — Show this help message"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


def create_bot_app() -> Application:
    """Create and configure the Telegram bot application."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("ask", handle_ask))
    app.add_handler(CommandHandler("help", handle_help))
    return app
