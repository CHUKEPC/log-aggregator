"""In-memory storage backend for fast testing and local development.

Provides full feature parity with ElasticsearchLogStorage without external dependencies.
"""

import asyncio
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from log_aggregator.models.log_entry import LogEntry, LogFilter, LogLevel, LogStats
from log_aggregator.storage.base import LogStorage


class InMemoryLogStorage(LogStorage):
    """Thread-safe in-memory log store implementing LogStorage."""

    def __init__(self) -> None:
        """Initialize in-memory log container and synchronization lock."""
        self._logs: dict[str, LogEntry] = {}
        self._lock = asyncio.Lock()

    async def index_log(self, entry: LogEntry) -> None:
        """Store a single log entry."""
        async with self._lock:
            self._logs[entry.id] = entry

    async def bulk_index_logs(self, entries: list[LogEntry]) -> int:
        """Store multiple log entries."""
        async with self._lock:
            for entry in entries:
                self._logs[entry.id] = entry
        return len(entries)

    def _matches_filter(self, entry: LogEntry, filter_query: LogFilter) -> bool:
        """Determine if a log entry satisfies all filter conditions."""
        # Full text query matching message, service, or source
        if filter_query.query:
            q = filter_query.query.lower()
            if (
                q not in entry.message.lower()
                and q not in entry.service.lower()
                and q not in entry.source.lower()
            ):
                return False

        if filter_query.service and entry.service != filter_query.service:
            return False

        if filter_query.services and entry.service not in filter_query.services:
            return False

        if filter_query.level and entry.level != filter_query.level:
            return False

        if filter_query.levels and entry.level not in filter_query.levels:
            return False

        if filter_query.source and entry.source != filter_query.source:
            return False

        if filter_query.tags and not any(tag in entry.tags for tag in filter_query.tags):
            return False

        if filter_query.start_time:
            # Normalize to UTC comparison
            e_ts = (
                entry.timestamp if entry.timestamp.tzinfo else entry.timestamp.replace(tzinfo=UTC)
            )
            f_start = (
                filter_query.start_time
                if filter_query.start_time.tzinfo
                else filter_query.start_time.replace(tzinfo=UTC)
            )
            if e_ts < f_start:
                return False

        if filter_query.end_time:
            e_ts = (
                entry.timestamp if entry.timestamp.tzinfo else entry.timestamp.replace(tzinfo=UTC)
            )
            f_end = (
                filter_query.end_time
                if filter_query.end_time.tzinfo
                else filter_query.end_time.replace(tzinfo=UTC)
            )
            if e_ts > f_end:
                return False

        return True

    async def search_logs(self, filter_query: LogFilter) -> tuple[list[LogEntry], int]:
        """Search and paginate through stored in-memory logs."""
        async with self._lock:
            matched = [
                log for log in self._logs.values() if self._matches_filter(log, filter_query)
            ]

        # Sort by timestamp
        matched.sort(key=lambda x: x.timestamp, reverse=filter_query.sort_desc)
        total = len(matched)

        # Slice for pagination
        start = filter_query.offset
        end = start + filter_query.limit
        paged = matched[start:end]

        return paged, total

    async def get_log_by_id(self, log_id: str) -> LogEntry | None:
        """Fetch log entry by its ID."""
        async with self._lock:
            return self._logs.get(log_id)

    async def get_stats(self, filter_query: LogFilter) -> LogStats:
        """Calculate distribution statistics for matching logs."""
        async with self._lock:
            matched = [
                log for log in self._logs.values() if self._matches_filter(log, filter_query)
            ]

        total = len(matched)
        level_counts: Counter[str] = Counter()
        service_counts: Counter[str] = Counter()
        error_messages: Counter[str] = Counter()
        hourly_buckets: Counter[str] = Counter()

        for log in matched:
            level_counts[log.level.value] += 1
            service_counts[log.service] += 1

            if log.level in (LogLevel.ERROR, LogLevel.CRITICAL):
                error_messages[log.message] += 1

            # Format to hourly bucket string YYYY-MM-DDTHH:00:00Z
            bucket_key = log.timestamp.strftime("%Y-%m-%dT%H:00:00Z")
            hourly_buckets[bucket_key] += 1

        top_errors: list[dict[str, Any]] = [
            {"message": msg, "count": count} for msg, count in error_messages.most_common(10)
        ]

        histogram: list[dict[str, Any]] = [
            {"timestamp": ts, "count": count} for ts, count in sorted(hourly_buckets.items())
        ]

        return LogStats(
            total_logs=total,
            by_level=dict(level_counts),
            by_service=dict(service_counts),
            top_errors=top_errors,
            time_histogram=histogram,
        )

    async def delete_logs_before(self, timestamp: datetime) -> int:
        """Delete logs older than cutoff timestamp."""
        ts_utc = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=UTC)
        deleted_count = 0

        async with self._lock:
            to_delete: list[str] = []
            for log_id, log in self._logs.items():
                log_ts = (
                    log.timestamp if log.timestamp.tzinfo else log.timestamp.replace(tzinfo=UTC)
                )
                if log_ts < ts_utc:
                    to_delete.append(log_id)

            for log_id in to_delete:
                del self._logs[log_id]
                deleted_count += 1

        return deleted_count

    async def ping(self) -> bool:
        """In-memory backend is always accessible."""
        return True

    async def close(self) -> None:
        """Clear stored records on close."""
        async with self._lock:
            self._logs.clear()
