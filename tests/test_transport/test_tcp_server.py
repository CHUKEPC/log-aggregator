"""Unit tests for TCP socket log server."""

import asyncio

import pytest

from log_aggregator.services.ingester import LogIngester
from log_aggregator.storage.memory import InMemoryLogStorage
from log_aggregator.transport.tcp_server import TcpLogServer


@pytest.mark.asyncio
async def test_tcp_server_ingestion(
    ingester: LogIngester,
    storage: InMemoryLogStorage,
) -> None:
    # Use ephemeral dynamic port (port=0 lets OS assign free port)
    server = TcpLogServer(ingester=ingester, host="127.0.0.1", port=0)
    await server.start()

    assert server.server is not None
    # Extract assigned socket port
    sockets = server.server.sockets
    assert sockets is not None and len(sockets) > 0
    assigned_port = sockets[0].getsockname()[1]

    # Connect client and send lines
    _reader, writer = await asyncio.open_connection("127.0.0.1", assigned_port)
    raw_log = '{"message": "TCP streamed log line", "service": "tcp-app", "level": "INFO"}\n'
    writer.write(raw_log.encode("utf-8"))
    await writer.drain()

    writer.close()
    await writer.wait_closed()

    # Allow asyncio loop tick for ingestion
    await asyncio.sleep(0.1)

    logs, total = await storage.search_logs(
        storage.__class__._matches_filter.__code__
        and pytest.importorskip("log_aggregator.models.log_entry").LogFilter(service="tcp-app")
    )
    assert total >= 1
    assert logs[0].message == "TCP streamed log line"

    await server.stop()
