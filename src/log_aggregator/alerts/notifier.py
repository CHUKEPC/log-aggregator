"""Alert notification and history management.

Dispatches webhooks when alerts trigger and stores historical event records.
"""

import asyncio
import logging
from collections import deque
from typing import Any

import httpx

from log_aggregator.alerts.models import AlertEvent, AlertRule

logger = logging.getLogger(__name__)


class AlertNotifier:
    """Dispatches webhook alerts and stores recent event history."""

    def __init__(self, history_limit: int = 1000) -> None:
        """Initialize event history buffer and webhook HTTP client."""
        self._history: deque[AlertEvent] = deque(maxlen=history_limit)
        self._http_client: httpx.AsyncClient | None = None
        self._background_tasks: set[asyncio.Task[None]] = set()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or initialize shared HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=5.0)
        return self._http_client

    async def notify(self, rule: AlertRule, event: AlertEvent) -> None:
        """Record triggered event and dispatch webhook if configured."""
        self._history.appendleft(event)

        if not rule.webhook_url:
            return

        payload: dict[str, Any] = {
            "event_id": event.id,
            "rule_id": rule.id,
            "rule_name": rule.name,
            "condition": rule.condition.value,
            "count": event.count,
            "threshold": rule.threshold,
            "message": event.message,
            "triggered_at": event.triggered_at.isoformat(),
        }

        # Fire webhook in background task to avoid blocking log ingestion pipeline
        task = asyncio.create_task(self._send_webhook(rule.webhook_url, payload))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _send_webhook(self, url: str, payload: dict[str, Any]) -> None:
        """Send POST request to configured webhook URL."""
        try:
            client = await self._get_client()
            resp = await client.post(url, json=payload)
            if resp.status_code >= 400:
                logger.warning(
                    "Webhook notification to %s failed with status %d", url, resp.status_code
                )
        except Exception as exc:
            logger.warning("Error dispatching alert webhook to %s: %s", url, exc)

    def get_events(self, limit: int = 50) -> list[AlertEvent]:
        """Retrieve recent alert events."""
        return list(self._history)[:limit]

    async def close(self) -> None:
        """Close HTTP client session."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
