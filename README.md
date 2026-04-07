# holmes-bridge

Bridge service between Grafana alerts, HolmesGPT AI investigation, and Telegram.

## What it does

1. Receives Grafana alert webhooks
2. Sends them to HolmesGPT for AI-powered investigation
3. Formats the investigation results and sends them to Telegram
4. Supports interactive `/ask` commands from Telegram to query the AI agent

## Configuration

All configuration is done via environment variables — **no secrets in the code**.

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Yes | Telegram chat ID for notifications |
| `HOLMES_API_URL` | Yes | HolmesGPT API server URL (e.g., `http://holmes.holmesgpt.svc.cluster.local`) |
| `HOLMES_MODEL` | No | Model name from HolmesGPT modelList (default: `haiku`) |
| `GRAFANA_URL` | No | External Grafana URL for dashboard links (default: `https://grafana.segator.es`) |
| `LOG_LEVEL` | No | Logging level (default: `INFO`) |

## Development

```bash
pip install -r requirements.txt
TELEGRAM_BOT_TOKEN=test TELEGRAM_CHAT_ID=test HOLMES_API_URL=http://localhost:5050 \
  uvicorn app.main:app --reload --port 8080
```

## Docker

```bash
docker build -t holmes-bridge .
docker run -p 8080:8080 \
  -e TELEGRAM_BOT_TOKEN=... \
  -e TELEGRAM_CHAT_ID=... \
  -e HOLMES_API_URL=... \
  holmes-bridge
```

## License

MIT
