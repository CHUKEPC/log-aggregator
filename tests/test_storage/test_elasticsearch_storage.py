"""Unit tests for ElasticsearchLogStorage backend using mocked client."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from log_aggregator.config import Settings
from log_aggregator.exceptions import StorageError
from log_aggregator.models.log_entry import LogEntry, LogFilter, LogLevel
from log_aggregator.storage.elasticsearch import ElasticsearchLogStorage


@pytest.fixture
def mock_es_client() -> AsyncMock:
    client = AsyncMock()
    # Mock indices.exists and create
    client.indices.exists.return_value = True
    client.ping.return_value = True
    return client


@pytest.mark.asyncio
async def test_es_storage_index_single(mock_es_client: AsyncMock) -> None:
    settings = Settings()
    storage = ElasticsearchLogStorage(settings=settings, client=mock_es_client)

    entry = LogEntry(message="Service started", service="web", level=LogLevel.INFO)
    await storage.index_log(entry)

    mock_es_client.index.assert_called_once()
    call_kwargs = mock_es_client.index.call_args.kwargs
    assert call_kwargs["id"] == entry.id
    assert call_kwargs["document"]["message"] == "Service started"


@pytest.mark.asyncio
async def test_es_storage_bulk_index(mock_es_client: AsyncMock) -> None:
    settings = Settings()
    storage = ElasticsearchLogStorage(settings=settings, client=mock_es_client)

    entries = [
        LogEntry(message="Log 1", service="api"),
        LogEntry(message="Log 2", service="api"),
    ]

    with patch(
        "log_aggregator.storage.elasticsearch.async_bulk", new_callable=AsyncMock
    ) as mock_bulk:
        mock_bulk.return_value = (2, [])
        count = await storage.bulk_index_logs(entries)
        assert count == 2
        mock_bulk.assert_called_once()


@pytest.mark.asyncio
async def test_es_storage_search(mock_es_client: AsyncMock) -> None:
    settings = Settings()
    storage = ElasticsearchLogStorage(settings=settings, client=mock_es_client)

    now = datetime.now(UTC)
    mock_es_client.search.return_value = {
        "hits": {
            "total": {"value": 1, "relation": "eq"},
            "hits": [
                {
                    "_id": "doc-1",
                    "_source": {
                        "id": "doc-1",
                        "message": "Out of memory",
                        "service": "worker",
                        "level": "CRITICAL",
                        "source": "node-1",
                        "timestamp": now.isoformat(),
                        "metadata": {},
                        "tags": ["fatal"],
                    },
                }
            ],
        }
    }

    f = LogFilter(query="memory", service="worker", level=LogLevel.CRITICAL)
    results, total = await storage.search_logs(f)

    assert total == 1
    assert len(results) == 1
    assert results[0].message == "Out of memory"
    assert results[0].level == LogLevel.CRITICAL


@pytest.mark.asyncio
async def test_es_storage_stats_aggregation(mock_es_client: AsyncMock) -> None:
    settings = Settings()
    storage = ElasticsearchLogStorage(settings=settings, client=mock_es_client)

    mock_es_client.search.return_value = {
        "hits": {"total": 42},
        "aggregations": {
            "by_level": {
                "buckets": [{"key": "INFO", "doc_count": 30}, {"key": "ERROR", "doc_count": 12}]
            },
            "by_service": {"buckets": [{"key": "auth-service", "doc_count": 42}]},
            "time_histogram": {
                "buckets": [{"key_as_string": "2023-11-01T12:00:00Z", "doc_count": 42}]
            },
            "top_errors": {
                "error_messages": {"buckets": [{"key": "Connection timed out", "doc_count": 10}]}
            },
        },
    }

    stats = await storage.get_stats(LogFilter())
    assert stats.total_logs == 42
    assert stats.by_level["INFO"] == 30
    assert stats.by_level["ERROR"] == 12
    assert stats.by_service["auth-service"] == 42
    assert stats.top_errors[0]["message"] == "Connection timed out"
    assert stats.time_histogram[0]["count"] == 42


@pytest.mark.asyncio
async def test_es_storage_retention_and_ping(mock_es_client: AsyncMock) -> None:
    settings = Settings()
    storage = ElasticsearchLogStorage(settings=settings, client=mock_es_client)

    mock_es_client.delete_by_query.return_value = {"deleted": 150}
    cutoff = datetime.now(UTC)
    deleted = await storage.delete_logs_before(cutoff)
    assert deleted == 150

    # Ping
    assert await storage.ping() is True

    # Close
    await storage.close()
    mock_es_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_es_storage_error_handling(mock_es_client: AsyncMock) -> None:
    settings = Settings()
    storage = ElasticsearchLogStorage(settings=settings, client=mock_es_client)

    mock_es_client.index.side_effect = RuntimeError("ES connection refused")
    with pytest.raises(StorageError):
        await storage.index_log(LogEntry(message="test", service="test"))
