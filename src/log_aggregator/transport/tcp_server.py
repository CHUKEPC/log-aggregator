"""TCP socket log receiver.

Listens for streaming line-delimited log messages sent over raw TCP connections
(e.g., from syslog daemons, FluentBit, or netcat).
"""

import asyncio
import contextlib
import logging

from log_aggregator.services.ingester import LogIngester

logger = logging.getLogger(__name__)


class TcpLogServer:
    """Asyncio TCP server accepting raw log lines over socket connections."""

    def __init__(self, ingester: LogIngester, host: str = "0.0.0.0", port: int = 9000) -> None:
        """Initialize TCP server configuration."""
        self.ingester = ingester
        self.host = host
        self.port = port
        self.server: asyncio.Server | None = None
        self._is_running = False

    async def start(self) -> None:
        """Start listening for incoming TCP client connections."""
        if self._is_running:
            return

        self.server = await asyncio.start_server(
            self._handle_client,
            host=self.host,
            port=self.port,
        )
        self._is_running = True
        logger.info("TCP Log Server listening on %s:%d", self.host, self.port)

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Process stream from an individual connected TCP client."""
        client_address = writer.get_extra_info("peername")
        source_id = f"tcp-{client_address[0]}" if client_address else "tcp"
        logger.debug("New TCP client connection from %s", client_address)

        buffer: list[str] = []
        try:
            while not reader.at_eof():
                line_bytes = await reader.readline()
                if not line_bytes:
                    break

                line = line_bytes.decode("utf-8", errors="replace").strip()
                if line:
                    buffer.append(line)

                # Batch flush periodically to maximize throughput
                if len(buffer) >= 50:
                    await self.ingester.ingest_raw_batch(
                        lines=buffer,
                        source=source_id,
                    )
                    buffer.clear()

            # Flush remaining lines on connection close
            if buffer:
                await self.ingester.ingest_raw_batch(
                    lines=buffer,
                    source=source_id,
                )
                buffer.clear()
        except Exception as exc:
            logger.warning("Error processing TCP client %s: %s", client_address, exc)
        finally:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()

    async def stop(self) -> None:
        """Stop TCP server and close socket listener."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self._is_running = False
            logger.info("TCP Log Server stopped")
