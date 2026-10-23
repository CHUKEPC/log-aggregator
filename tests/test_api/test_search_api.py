"""API tests for log search and retrieval endpoints."""

import httpx
import pytest

from log_aggregator.models.log_entry import LogEntry
from log_aggregator.storage.memory import InMemoryLogStorage


@pytest.mark.asyncio
async def test_search_and_pagination(
    client: httpx.AsyncClient,
    storage: InMemoryLogStorage,
    sample_log_entries: list[LogEntry],
) -> None:
    await storage.bulk_index_logs(sample_log_entries)

    # Search without filters
    resp = await client.get("/api/v1/search")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == len(sample_log_entries)
    assert len(data["logs"]) == len(sample_log_entries)

    # Search with service filter
    resp_svc = await client.get("/api/v1/search?service=payment-service")
    assert resp_svc.status_code == 200
    assert resp_svc.json()["total"] == 2

    # Search with level filter
    resp_lvl = await client.get("/api/v1/search?level=CRITICAL")
    assert resp_lvl.status_code == 200
    assert resp_lvl.json()["total"] == 1

    # Search with keyword
    resp_q = await client.get("/api/v1/search?q=saturated")
    assert resp_q.status_code == 200
    assert resp_q.json()["total"] == 1

    # Pagination: limit & offset
    resp_p = await client.get("/api/v1/search?limit=2&offset=1")
    assert resp_p.status_code == 200
    data_p = resp_p.json()
    assert len(data_p["logs"]) == 2
    assert data_p["limit"] == 2
    assert data_p["offset"] == 1


@pytest.mark.asyncio
async def test_get_log_by_id(
    client: httpx.AsyncClient,
    storage: InMemoryLogStorage,
    sample_log_entries: list[LogEntry],
) -> None:
    await storage.bulk_index_logs(sample_log_entries)
    target_id = sample_log_entries[0].id

    # Found
    resp = await client.get(f"/api/v1/logs/{target_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == target_id

    # Not found
    resp_404 = await client.get("/api/v1/logs/00000000-0000-0000-0000-000000000000")
    assert resp_404.status_code == 404
