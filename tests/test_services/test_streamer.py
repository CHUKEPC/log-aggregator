"""Unit tests for LogStreamer WebSocket pub/sub manager."""

from unittest.mock import AsyncMock

import pytest
from starlette.websockets import WebSocket

from log_aggregator.models.log_entry import LogEntry, LogLevel
from log_aggregator.services.streamer import LogStreamer


@pytest.mark.asyncio
async def test_streamer_connect_and_broadcast() -> None:
    streamer = LogStreamer()
    mock_ws = AsyncMock(spec=WebSocket)

    sub = await streamer.connect(
        websocket=mock_ws,
        service="payment-service",
        min_level=LogLevel.WARNING,
        query="failed",
    )
    assert len(streamer._subscribers) == 1

    matching_log = LogEntry(
        message="Transaction failed due to network",
        service="payment-service",
        level=LogLevel.ERROR,
    )
    non_matching_service = LogEntry(
        message="Transaction failed",
        service="auth-service",
        level=LogLevel.ERROR,
    )
    non_matching_level = LogEntry(
        message="Transaction failed",
        service="payment-service",
        level=LogLevel.INFO,
    )

    await streamer.broadcast([matching_log, non_matching_service, non_matching_level])

    # Only matching_log should be sent to mock_ws
    assert mock_ws.send_text.call_count == 1

    # Disconnect
    await streamer.disconnect(sub)
    assert len(streamer._subscribers) == 0
