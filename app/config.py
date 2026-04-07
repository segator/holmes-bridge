"""Configuration loaded from environment variables. No secrets in code."""

import os


TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID: str = os.environ["TELEGRAM_CHAT_ID"]
HOLMES_API_URL: str = os.environ["HOLMES_API_URL"]
HOLMES_MODEL: str = os.environ.get("HOLMES_MODEL", "haiku")
GRAFANA_URL: str = os.environ.get("GRAFANA_URL", "")
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

# Comma-separated list of allowed Telegram chat IDs for bot commands.
# If empty, defaults to TELEGRAM_CHAT_ID only.
_allowed_raw = os.environ.get("ALLOWED_CHAT_IDS", "")
ALLOWED_CHAT_IDS: set[int] = (
    {int(cid.strip()) for cid in _allowed_raw.split(",") if cid.strip()}
    if _allowed_raw
    else {int(TELEGRAM_CHAT_ID)}
)
