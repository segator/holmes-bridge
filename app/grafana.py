"""Grafana webhook payload parser."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def parse_grafana_webhook(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse Grafana unified alerting webhook payload into alert items.

    Grafana sends a payload with top-level fields and an 'alerts' list.
    Each alert has: status, labels, annotations, startsAt, endsAt,
    generatorURL, fingerprint, values, etc.

    Returns a list of dicts with:
      - title: alert name
      - description: alert summary + description
      - status: firing | resolved
      - labels: original labels dict
      - dashboard_url: link to Grafana dashboard (if available)
      - panel_id: panel ID (if available)
    """
    alerts_raw = payload.get("alerts", [])
    parsed = []

    for alert in alerts_raw:
        status = alert.get("status", "unknown")
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})

        title = labels.get("alertname", "Unknown Alert")
        summary = annotations.get("summary", "")
        description = annotations.get("description", "")

        # Build a rich description for Holmes
        desc_parts = []
        if summary:
            desc_parts.append(f"Summary: {summary}")
        if description:
            desc_parts.append(f"Description: {description}")
        desc_parts.append(f"Status: {status}")

        # Include label context
        severity = labels.get("severity", "")
        if severity:
            desc_parts.append(f"Severity: {severity}")

        # Include values if present (Grafana sends current metric values)
        values = alert.get("values", {})
        if values:
            values_str = ", ".join(f"{k}={v}" for k, v in values.items())
            desc_parts.append(f"Values: {values_str}")

        # Dashboard link
        dashboard_uid = annotations.get("__dashboardUid__", "")
        panel_id = annotations.get("__panelId__", "")

        parsed.append(
            {
                "title": title,
                "description": "\n".join(desc_parts),
                "status": status,
                "labels": labels,
                "dashboard_uid": dashboard_uid,
                "panel_id": panel_id,
            }
        )

    return parsed
