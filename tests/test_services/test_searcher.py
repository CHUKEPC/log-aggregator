"""Unit tests for LogSearcher service."""

import pytest

from log_aggregator.exceptions import NotFoundError
from log_aggregator.models.log_entry import LogEntry, LogFilter, LogLevel
from log_aggregator.services.searcher import LogSearcher
from log_aggregator.storage.memory import InMemoryLogStorage


@pytest.mark.asyncio
async def test_searcher_operations(
    searcher: LogSearcher,
    storage: InMemoryLogStorage,
    sample_log_entries: list[LogEntry],
) -> None:
    await storage.bulk_index_logs(sample_log_entries)

    # Search with filter
    logs, total = await searcher.search(LogFilter(level=LogLevel.ERROR))
    assert total == 1
    assert logs[0].level == LogLevel.ERROR

    # Get by ID
    first_id = sample_log_entries[0].id
    entry = await searcher.get_by_id(first_id)
    assert entry.id == first_id

    # Get non-existent raises NotFoundError
    with pytest.raises(NotFoundError):
        await searcher.get_by_id("non-existent-id")

    # Get stats
    stats = await searcher.get_stats(LogFilter())
    assert stats.total_logs == len(sample_log_entries)
