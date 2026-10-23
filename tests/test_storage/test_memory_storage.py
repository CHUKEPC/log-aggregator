"""Unit tests for InMemoryLogStorage backend."""

from datetime import UTC, datetime, timedelta

import pytest

from log_aggregator.models.log_entry import LogEntry, LogFilter, LogLevel
from log_aggregator.storage.memory import InMemoryLogStorage


@pytest.mark.asyncio
async def test_memory_storage_index_and_retrieve(
    storage: InMemoryLogStorage,
    sample_log_entries: list[LogEntry],
) -> None:
    # Test single indexing
    await storage.index_log(sample_log_entries[0])
    retrieved = await storage.get_log_by_id(sample_log_entries[0].id)
    assert retrieved is not None
    assert retrieved.message == sample_log_entries[0].message

    # Test non-existent ID
    missing = await storage.get_log_by_id("non-existent-uuid")
    assert missing is None

    # Test bulk indexing
    count = await storage.bulk_index_logs(sample_log_entries[1:])
    assert count == len(sample_log_entries) - 1


@pytest.mark.asyncio
async def test_memory_storage_filters(
    storage: InMemoryLogStorage,
    sample_log_entries: list[LogEntry],
) -> None:
    await storage.bulk_index_logs(sample_log_entries)

    # Filter by service
    f_service = LogFilter(service="payment-service")
    logs, total = await storage.search_logs(f_service)
    assert total == 2
    assert all(item.service == "payment-service" for item in logs)

    # Filter by level
    f_level = LogFilter(level=LogLevel.ERROR)
    logs_err, total_err = await storage.search_logs(f_level)
    assert total_err == 1
    assert logs_err[0].level == LogLevel.ERROR

    # Filter by multiple levels
    f_levels = LogFilter(levels=[LogLevel.ERROR, LogLevel.CRITICAL])
    _logs_crit, total_crit = await storage.search_logs(f_levels)
    assert total_crit == 2

    # Filter by query keyword
    f_query = LogFilter(query="credit card")
    logs_q, total_q = await storage.search_logs(f_query)
    assert total_q == 1
    assert "credit card" in logs_q[0].message

    # Filter by tags
    f_tags = LogFilter(tags=["login"])
    logs_tag, total_tag = await storage.search_logs(f_tags)
    assert total_tag == 1
    assert "login" in logs_tag[0].tags


@pytest.mark.asyncio
async def test_memory_storage_time_range_and_pagination(
    storage: InMemoryLogStorage,
    sample_log_entries: list[LogEntry],
) -> None:
    await storage.bulk_index_logs(sample_log_entries)
    now = datetime.now(UTC)

    # Filter by time range (last 8 minutes: logs from 5min and 1min ago)
    f_time = LogFilter(start_time=now - timedelta(minutes=8), end_time=now)
    _logs, total = await storage.search_logs(f_time)
    assert total >= 2

    # Pagination: limit and offset
    f_page1 = LogFilter(limit=2, offset=0, sort_desc=True)
    logs_p1, total_p1 = await storage.search_logs(f_page1)
    assert len(logs_p1) == 2
    assert total_p1 == len(sample_log_entries)

    f_page2 = LogFilter(limit=2, offset=2, sort_desc=True)
    logs_p2, _ = await storage.search_logs(f_page2)
    assert len(logs_p2) == 2
    assert logs_p1[0].id != logs_p2[0].id


@pytest.mark.asyncio
async def test_memory_storage_statistics(
    storage: InMemoryLogStorage,
    sample_log_entries: list[LogEntry],
) -> None:
    await storage.bulk_index_logs(sample_log_entries)

    stats = await storage.get_stats(LogFilter())
    assert stats.total_logs == len(sample_log_entries)
    assert stats.by_service["auth-service"] == 2
    assert stats.by_service["payment-service"] == 2
    assert stats.by_level["ERROR"] == 1
    assert stats.by_level["WARNING"] == 1
    assert len(stats.top_errors) >= 1
    assert len(stats.time_histogram) >= 1


@pytest.mark.asyncio
async def test_memory_storage_retention_and_close(
    storage: InMemoryLogStorage,
    sample_log_entries: list[LogEntry],
) -> None:
    await storage.bulk_index_logs(sample_log_entries)
    now = datetime.now(UTC)

    # Delete logs older than 7 minutes (logs from 15min and 10min ago)
    purged = await storage.delete_logs_before(now - timedelta(minutes=7))
    assert purged == 2

    _remaining, total = await storage.search_logs(LogFilter())
    assert total == 3

    assert await storage.ping() is True
    await storage.close()
    assert len(storage._logs) == 0
