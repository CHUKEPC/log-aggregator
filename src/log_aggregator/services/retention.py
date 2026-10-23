"""Log retention policy service.

Enforces automated and on-demand pruning of expired log records based on TTL.
"""

import logging
from datetime import UTC, datetime, timedelta

from log_aggregator.config import Settings
from log_aggregator.storage.base import LogStorage

logger = logging.getLogger(__name__)


class RetentionService:
    """Manages lifecycle and cleanup of stored log records."""

    def __init__(self, storage: LogStorage, settings: Settings) -> None:
        """Initialize with storage backend and application settings."""
        self.storage = storage
        self.default_retention_days = settings.RETENTION_DAYS

    async def cleanup_old_logs(self, retention_days: int | None = None) -> int:
        """Purge logs older than the designated retention period.

        Args:
            retention_days: Optional custom TTL in days. Defaults to settings.RETENTION_DAYS.

        Returns:
            Number of purged log documents.
        """
        days = retention_days if retention_days is not None else self.default_retention_days
        if days <= 0:
            logger.info("Retention cleanup skipped: retention_days is 0 (keep indefinitely)")
            return 0

        cutoff = datetime.now(UTC) - timedelta(days=days)
        deleted_count = await self.storage.delete_logs_before(cutoff)
        logger.info(
            "Retention cleanup completed: purged %d logs older than %d days (%s)",
            deleted_count,
            days,
            cutoff.isoformat(),
        )
        return deleted_count
