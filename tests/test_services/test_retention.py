"""Unit tests for RetentionService."""

from datetime import UTC, datetime, timedelta

import pytest

from log_aggregator.config import Settings
from log_aggregator.models.log_entry import LogEntry
from log_aggregator.services.retention import RetentionService
from log_aggregator.storage.memory import InMemoryLogStorage


@pytest.mark.asyncio
async def test_retention_service_cleanup(storage: InMemoryLogStorage) -> None:
    now = datetime.now(UTC)
    old_log = LogEntry(message="old", service="svc", timestamp=now - timedelta(days=40))
    recent_log = LogEntry(message="recent", service="svc", timestamp=now - timedelta(days=5))

    await storage.bulk_index_logs([old_log, recent_log])

    settings = Settings(RETENTION_DAYS=30)
    service = RetentionService(storage=storage, settings=settings)

    purged = await service.cleanup_old_logs()
    assert purged == 1

    remaining_old = await storage.get_log_by_id(old_log.id)
    assert remaining_old is None

    remaining_recent = await storage.get_log_by_id(recent_log.id)
    assert remaining_recent is not None


@pytest.mark.asyncio
async def test_retention_service_zero_days_skips(storage: InMemoryLogStorage) -> None:
    settings = Settings(RETENTION_DAYS=0)
    service = RetentionService(storage=storage, settings=settings)
    purged = await service.cleanup_old_logs()
    assert purged == 0
