"""API tests for log statistics and metrics endpoints."""

import httpx
import pytest

from log_aggregator.models.log_entry import LogEntry
from log_aggregator.storage.memory import InMemoryLogStorage


@pytest.mark.asyncio
async def test_get_stats_api(
    client: httpx.AsyncClient,
    storage: InMemoryLogStorage,
    sample_log_entries: list[LogEntry],
) -> None:
    await storage.bulk_index_logs(sample_log_entries)

    response = await client.get("/api/v1/stats")
    assert response.status_code == 200
    data = response.json()

    assert data["total_logs"] == len(sample_log_entries)
    assert "by_level" in data
    assert "by_service" in data
    assert "top_errors" in data
    assert "time_histogram" in data

    assert data["by_service"]["auth-service"] == 2
    assert data["by_level"]["ERROR"] == 1


@pytest.mark.asyncio
async def test_get_stats_filtered_by_service(
    client: httpx.AsyncClient,
    storage: InMemoryLogStorage,
    sample_log_entries: list[LogEntry],
) -> None:
    await storage.bulk_index_logs(sample_log_entries)

    response = await client.get("/api/v1/stats?service=payment-service")
    assert response.status_code == 200
    data = response.json()

    assert data["total_logs"] == 2
    assert "payment-service" in data["by_service"]
    assert "auth-service" not in data["by_service"]
