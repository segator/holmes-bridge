"""Holmes Bridge — Grafana webhook -> HolmesGPT -> Telegram.

Main FastAPI application. All secrets come from environment variables.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response

from app.config import LOG_LEVEL
from app.grafana import parse_grafana_webhook
from app.telegram_handler import (
    create_bot_app,
    send_investigation_result,
    send_message,
)
from app import holmes

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Suppress noisy 409 Conflict errors from Telegram polling.
# These are non-fatal — the library retries automatically and the bot
# continues to receive updates. The 409 happens due to httpx connection
# pooling interactions with Telegram's getUpdates long-polling.
logging.getLogger("telegram.ext.Updater").setLevel(logging.CRITICAL)

# Telegram bot application (for /ask commands via polling)
bot_app = create_bot_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start/stop the Telegram bot polling alongside the web server."""
    logger.info("Starting Telegram bot polling...")
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling(
        drop_pending_updates=True,
        allowed_updates=["message"],  # Only receive message updates
        poll_interval=1.0,  # 1s delay between polls to avoid 409 conflicts
    )
    logger.info("Holmes Bridge started")
    yield
    logger.info("Shutting down Telegram bot...")
    await bot_app.updater.stop()
    await bot_app.stop()
    await bot_app.shutdown()


app = FastAPI(title="Holmes Bridge", lifespan=lifespan)


@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/api/alerts")
async def receive_grafana_alerts(request: Request):
    """Receive Grafana webhook alerts and investigate them with HolmesGPT.

    Only investigates 'firing' alerts — ignores 'resolved'.
    Investigation runs in background to avoid webhook timeout.
    """
    payload: dict[str, Any] = await request.json()
    alerts = parse_grafana_webhook(payload)

    firing = [a for a in alerts if a["status"] == "firing"]
    if not firing:
        logger.info("No firing alerts in webhook payload, skipping")
        return {"status": "ok", "investigated": 0}

    logger.info("Received %d firing alert(s), starting investigation", len(firing))

    # Run investigations in background so Grafana doesn't timeout
    for alert in firing:
        asyncio.create_task(_investigate_and_notify(alert))

    return {"status": "ok", "investigated": len(firing)}


async def _investigate_and_notify(alert: dict[str, Any]) -> None:
    """Investigate a single alert with HolmesGPT and send result to Telegram."""
    title = alert["title"]
    try:
        result = await holmes.investigate(
            title=title,
            description=alert["description"],
            context={"labels": alert["labels"]},
        )
        await send_investigation_result(title, result)
    except Exception:
        logger.exception("Investigation failed for alert: %s", title)
        await send_message(
            f"<b>Investigation failed</b>\n"
            f"Alert: {title}\n"
            f"Check bridge logs for details."
        )
