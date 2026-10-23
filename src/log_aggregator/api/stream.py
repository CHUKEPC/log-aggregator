"""WebSocket streaming API endpoint.

Provides real-time log tailing functionality with server-side filtering.
"""

from typing import Annotated

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from log_aggregator.api.deps import get_streamer
from log_aggregator.models.log_entry import LogLevel

router = APIRouter(tags=["Streaming"])


@router.websocket("/ws/logs")
@router.websocket("/stream/ws")
async def websocket_log_stream(
    websocket: WebSocket,
    service: Annotated[str | None, Query(description="Filter logs by service")] = None,
    min_level: Annotated[LogLevel | None, Query(description="Minimum severity level")] = None,
    query: Annotated[str | None, Query(description="Search keyword filter")] = None,
) -> None:
    """Stream live logs to connected WebSocket clients in real time."""
    streamer = get_streamer()
    subscriber = await streamer.connect(
        websocket=websocket,
        service=service,
        min_level=min_level,
        query=query,
    )
    try:
        # Keep connection open until client disconnects
        while True:
            # Handle any incoming client ping or message
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await streamer.disconnect(subscriber)
