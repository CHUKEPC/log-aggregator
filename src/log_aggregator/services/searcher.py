"""Log search and analytics service.

Provides full-text search, multi-field filtering, and aggregate statistics calculation.
"""

from log_aggregator.exceptions import NotFoundError
from log_aggregator.models.log_entry import LogEntry, LogFilter, LogStats
from log_aggregator.storage.base import LogStorage


class LogSearcher:
    """Business logic for querying log records and metrics."""

    def __init__(self, storage: LogStorage) -> None:
        """Initialize with storage backend."""
        self.storage = storage

    async def search(self, filter_query: LogFilter) -> tuple[list[LogEntry], int]:
        """Search logs by query, severity, service, and timestamp range."""
        return await self.storage.search_logs(filter_query)

    async def get_by_id(self, log_id: str) -> LogEntry:
        """Retrieve a log entry by its unique identifier or raise NotFoundError."""
        entry = await self.storage.get_log_by_id(log_id)
        if not entry:
            raise NotFoundError(f"Log entry '{log_id}' not found")
        return entry

    async def get_stats(self, filter_query: LogFilter) -> LogStats:
        """Generate summary statistics and distribution histograms."""
        return await self.storage.get_stats(filter_query)
