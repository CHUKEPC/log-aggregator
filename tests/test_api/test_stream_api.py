"""API tests for WebSocket real-time log streaming."""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from starlette.websockets import WebSocket, WebSocketDisconnect

from log_aggregator.api.stream import websocket_log_stream
from log_aggregator.models.log_entry import LogLevel
from log_aggregator.services.streamer import LogStreamer


def test_websocket_stream_endpoint_client(app: FastAPI) -> None:
    """Test WebSocket connection via Starlette TestClient."""
    client = TestClient(app)

    with client.websocket_connect("/ws/logs?service=frontend-app&min_level=INFO") as ws:
        # Send a message to keep server receive loop progressing
        ws.send_text("ping")


@pytest.mark.asyncio
async def test_websocket_stream_lifecycle(streamer: LogStreamer) -> None:
    """Test full WebSocket endpoint lifecycle with async mock."""
    mock_ws = AsyncMock(spec=WebSocket)
    # Simulate client disconnect upon receive
    mock_ws.receive_text.side_effect = WebSocketDisconnect(code=1000)

    # Call the endpoint directly
    await websocket_log_stream(
        websocket=mock_ws,
        service="order-service",
        min_level=LogLevel.WARNING,
        query="failed",
    )

    mock_ws.accept.assert_called_once()
    assert len(streamer._subscribers) == 0
