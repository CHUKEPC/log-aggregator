"""Storage abstraction for log indexing, searching, and analytics.

Defines the interface implemented by both Elasticsearch and in-memory backends.
"""

from abc import ABC, abstractmethod
from datetime import datetime

from log_aggregator.models.log_entry import LogEntry, LogFilter, LogStats


class LogStorage(ABC):
    """Abstract interface for log persistence and search operations."""

    @abstractmethod
    async def index_log(self, entry: LogEntry) -> None:
        """Persist a single log entry into storage.

        Args:
            entry: Structured log record.
        """

    @abstractmethod
    async def bulk_index_logs(self, entries: list[LogEntry]) -> int:
        """Bulk index multiple log records.

        Args:
            entries: List of LogEntry instances.

        Returns:
            Number of successfully indexed records.
        """

    @abstractmethod
    async def search_logs(self, filter_query: LogFilter) -> tuple[list[LogEntry], int]:
        """Search and filter stored logs according to criteria.

        Args:
            filter_query: Search parameters and pagination.

        Returns:
            Tuple of (matching logs list, total match count).
        """

    @abstractmethod
    async def get_log_by_id(self, log_id: str) -> LogEntry | None:
        """Retrieve a single log entry by its unique ID.

        Args:
            log_id: UUID of log entry.

        Returns:
            LogEntry if found, None otherwise.
        """

    @abstractmethod
    async def get_stats(self, filter_query: LogFilter) -> LogStats:
        """Calculate aggregate metrics and histograms over matching logs.

        Args:
            filter_query: Scope filter for aggregations.

        Returns:
            LogStats summary.
        """

    @abstractmethod
    async def delete_logs_before(self, timestamp: datetime) -> int:
        """Delete all logs older than the specified timestamp.

        Args:
            timestamp: Cutoff datetime in UTC.

        Returns:
            Number of deleted log documents.
        """

    @abstractmethod
    async def ping(self) -> bool:
        """Check if storage backend is healthy and accessible.

        Returns:
            True if healthy, False otherwise.
        """

    @abstractmethod
    async def close(self) -> None:
        """Gracefully close connections to the storage backend."""
