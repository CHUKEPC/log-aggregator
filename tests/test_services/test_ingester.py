"""Unit tests for LogIngester service."""

import pytest

from log_aggregator.models.log_entry import LogFormat, LogLevel
from log_aggregator.schemas.log import (
    LogCreateRequest,
    RawLogCreateRequest,
)
from log_aggregator.services.ingester import LogIngester
from log_aggregator.storage.memory import InMemoryLogStorage


@pytest.mark.asyncio
async def test_ingester_single_structured(
    ingester: LogIngester,
    storage: InMemoryLogStorage,
) -> None:
    req = LogCreateRequest(
        message="Service health check OK",
        service="monitor-service",
        level=LogLevel.INFO,
        tags=["health"],
    )

    entry = await ingester.ingest_single(req)
    assert entry.id is not None
    assert entry.message == "Service health check OK"

    retrieved = await storage.get_log_by_id(entry.id)
    assert retrieved is not None
    assert retrieved.service == "monitor-service"


@pytest.mark.asyncio
async def test_ingester_batch_structured(
    ingester: LogIngester,
    storage: InMemoryLogStorage,
) -> None:
    reqs = [
        LogCreateRequest(message="Batch 1", service="svc-1"),
        LogCreateRequest(message="Batch 2", service="svc-2"),
    ]

    resp = await ingester.ingest_batch(reqs)
    assert resp.ingested == 2
    assert len(resp.errors) == 0


@pytest.mark.asyncio
async def test_ingester_raw_single_and_batch(
    ingester: LogIngester,
    storage: InMemoryLogStorage,
) -> None:
    # Ingest raw JSON
    raw_json_req = RawLogCreateRequest(
        raw='{"message": "JSON raw log", "level": "WARNING", "service": "raw-app"}',
        format=LogFormat.JSON,
    )
    entry = await ingester.ingest_raw_single(raw_json_req)
    assert entry.message == "JSON raw log"
    assert entry.level == LogLevel.WARNING
    assert entry.service == "raw-app"

    # Ingest raw batch
    lines = [
        "2023-10-10 12:00:00 [INFO] [app1] line one",
        "2023-10-10 12:00:01 [ERROR] [app1] line two",
    ]
    batch_resp = await ingester.ingest_raw_batch(lines, source="test-tcp")
    assert batch_resp.ingested == 2
    assert len(batch_resp.errors) == 0
