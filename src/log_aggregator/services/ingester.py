"""Log ingestion service.

Handles parsing, persistence, real-time WebSocket streaming broadcast,
and alert threshold evaluation.
"""

import logging

from log_aggregator.alerts.evaluator import AlertEvaluator
from log_aggregator.alerts.notifier import AlertNotifier
from log_aggregator.models.log_entry import LogEntry, LogFormat
from log_aggregator.parsers.factory import parse_raw_line
from log_aggregator.schemas.log import (
    IngestResponse,
    LogCreateRequest,
    RawLogCreateRequest,
)
from log_aggregator.services.streamer import LogStreamer
from log_aggregator.storage.base import LogStorage

logger = logging.getLogger(__name__)


class LogIngester:
    """Orchestrates log ingestion across parsing, storage, streaming, and alerting."""

    def __init__(
        self,
        storage: LogStorage,
        streamer: LogStreamer,
        evaluator: AlertEvaluator,
        notifier: AlertNotifier,
    ) -> None:
        """Initialize dependencies."""
        self.storage = storage
        self.streamer = streamer
        self.evaluator = evaluator
        self.notifier = notifier

    async def ingest_single(self, request: LogCreateRequest) -> LogEntry:
        """Process and persist a single structured log entry."""
        entry = request.to_domain()
        await self.storage.index_log(entry)

        # Broadcast to real-time streams
        await self.streamer.broadcast([entry])

        # Evaluate alert rules
        events = self.evaluator.evaluate([entry])
        for event in events:
            rule = self.evaluator.get_rule(event.rule_id)
            if rule:
                await self.notifier.notify(rule, event)

        return entry

    async def ingest_batch(self, requests: list[LogCreateRequest]) -> IngestResponse:
        """Process and bulk-persist a list of structured log entries."""
        if not requests:
            return IngestResponse(ingested=0, errors=[])

        entries = [req.to_domain() for req in requests]
        indexed_count = await self.storage.bulk_index_logs(entries)

        # Stream broadcast
        await self.streamer.broadcast(entries)

        # Evaluate alerts
        events = self.evaluator.evaluate(entries)
        for event in events:
            rule = self.evaluator.get_rule(event.rule_id)
            if rule:
                await self.notifier.notify(rule, event)

        return IngestResponse(ingested=indexed_count, errors=[])

    async def ingest_raw_single(self, request: RawLogCreateRequest) -> LogEntry:
        """Parse and ingest a single unparsed raw log line."""
        entry = parse_raw_line(
            raw=request.raw,
            explicit_format=request.format,
            default_service=request.service or "default",
            source=request.source,
        )
        await self.storage.index_log(entry)
        await self.streamer.broadcast([entry])

        events = self.evaluator.evaluate([entry])
        for event in events:
            rule = self.evaluator.get_rule(event.rule_id)
            if rule:
                await self.notifier.notify(rule, event)

        return entry

    async def ingest_raw_batch(
        self,
        lines: list[str],
        explicit_format: LogFormat | None = None,
        service: str | None = None,
        source: str = "batch-raw",
    ) -> IngestResponse:
        """Parse and bulk-persist multiple unparsed raw log lines."""
        entries: list[LogEntry] = []
        errors: list[str] = []

        for idx, line in enumerate(lines):
            try:
                entry = parse_raw_line(
                    raw=line,
                    explicit_format=explicit_format,
                    default_service=service or "default",
                    source=source,
                )
                entries.append(entry)
            except Exception as exc:
                errors.append(f"Line {idx + 1} parse error: {exc}")

        indexed_count = 0
        if entries:
            indexed_count = await self.storage.bulk_index_logs(entries)
            await self.streamer.broadcast(entries)

            events = self.evaluator.evaluate(entries)
            for event in events:
                rule = self.evaluator.get_rule(event.rule_id)
                if rule:
                    await self.notifier.notify(rule, event)

        return IngestResponse(ingested=indexed_count, errors=errors)
