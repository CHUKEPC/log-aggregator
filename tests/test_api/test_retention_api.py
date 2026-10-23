"""API tests for retention cleanup endpoints."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from log_aggregator.models.log_entry import LogEntry
from log_aggregator.storage.memory import InMemoryLogStorage


@pytest.mark.asyncio
async def test_retention_cleanup_api(
    client: httpx.AsyncClient,
    storage: InMemoryLogStorage,
    auth_headers: dict[str, str],
) -> None:
    now = datetime.now(UTC)
    old_log = LogEntry(message="expired log", service="svc", timestamp=now - timedelta(days=60))
    await storage.index_log(old_log)

    response = await client.post(
        "/api/v1/retention/cleanup?days=30",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["purged_count"] == 1
    assert data["retention_days"] == 30
