"""WebSocket real-time log streaming pub/sub manager.

Maintains active client connections with per-client filters and broadcasts
incoming logs in real time (similar to tail -f).
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

from starlette.websockets import WebSocket

from log_aggregator.models.log_entry import LogEntry, LogLevel

logger = logging.getLogger(__name__)


@dataclass
class StreamSubscriber:
    """Subscription state and filter preferences for an active WebSocket client."""

    websocket: WebSocket
    service: str | None = None
    min_level: LogLevel | None = None
    query: str | None = None


class LogStreamer:
    """Pub/Sub manager for real-time log streaming over WebSockets."""

    def __init__(self) -> None:
        """Initialize connection lock and subscriber list."""
        self._subscribers: set[StreamSubscriber] = set()
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        service: str | None = None,
        min_level: LogLevel | None = None,
        query: str | None = None,
    ) -> StreamSubscriber:
        """Accept WebSocket connection and register subscriber with filters."""
        await websocket.accept()
        sub = StreamSubscriber(
            websocket=websocket,
            service=service,
            min_level=min_level,
            query=query.lower() if query else None,
        )
        async with self._lock:
            self._subscribers.add(sub)
        logger.info("WebSocket client connected. Active subscribers: %d", len(self._subscribers))
        return sub

    async def disconnect(self, subscriber: StreamSubscriber) -> None:
        """Unregister a disconnected WebSocket client."""
        async with self._lock:
            self._subscribers.discard(subscriber)
        logger.info(
            "WebSocket client disconnected. Active subscribers: %d", len(self._subscribers)
        )

    def _matches(self, entry: LogEntry, sub: StreamSubscriber) -> bool:
        """Check if log entry satisfies subscriber's filtering criteria."""
        if sub.service and entry.service != sub.service:
            return False

        if sub.min_level:
            # Severity hierarchy ordering
            hierarchy = {
                LogLevel.DEBUG: 1,
                LogLevel.INFO: 2,
                LogLevel.WARNING: 3,
                LogLevel.ERROR: 4,
                LogLevel.CRITICAL: 5,
            }
            if hierarchy.get(entry.level, 0) < hierarchy.get(sub.min_level, 0):
                return False

        if sub.query:
            q = sub.query
            matched = (
                q in entry.message.lower()
                or q in entry.service.lower()
                or q in entry.source.lower()
            )
            if not matched:
                return False

        return True

    async def broadcast(self, entries: list[LogEntry]) -> None:
        """Send new matching log records to all connected subscribers."""
        if not entries:
            return

        async with self._lock:
            subscribers = list(self._subscribers)

        if not subscribers:
            return

        stale_subscribers: list[StreamSubscriber] = []

        for sub in subscribers:
            for entry in entries:
                if self._matches(entry, sub):
                    try:
                        payload: dict[str, Any] = entry.to_dict()
                        await sub.websocket.send_text(json.dumps(payload))
                    except Exception as exc:
                        logger.debug("Failed sending log to WebSocket subscriber: %s", exc)
                        stale_subscribers.append(sub)
                        break

        if stale_subscribers:
            async with self._lock:
                for sub in stale_subscribers:
                    self._subscribers.discard(sub)
