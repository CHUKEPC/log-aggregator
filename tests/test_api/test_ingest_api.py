"""API tests for log ingestion endpoints."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_ingest_single_structured(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    payload = {
        "message": "User completed payment",
        "service": "payment-api",
        "level": "INFO",
        "source": "api-gateway",
        "metadata": {"order_id": 12345},
        "tags": ["payment", "checkout"],
    }

    response = await client.post("/api/v1/ingest", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "User completed payment"
    assert data["service"] == "payment-api"
    assert data["metadata"]["order_id"] == 12345


@pytest.mark.asyncio
async def test_ingest_batch_structured(
    client: httpx.AsyncClient,
    service_api_key_headers: dict[str, str],
) -> None:
    payload = {
        "logs": [
            {"message": "Log batch 1", "service": "svc-a", "level": "DEBUG"},
            {"message": "Log batch 2", "service": "svc-b", "level": "WARNING"},
        ]
    }

    response = await client.post(
        "/api/v1/ingest/batch",
        json=payload,
        headers=service_api_key_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["ingested"] == 2
    assert len(data["errors"]) == 0


@pytest.mark.asyncio
async def test_ingest_raw_single_and_batch(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    # Single raw Nginx
    raw_payload = {
        "raw": '10.0.0.1 - - [10/Oct/2023:13:55:36 +0000] "GET /api/v1/health HTTP/1.1" 200 15 "-" "-"',
        "format": "NGINX",
        "service": "nginx-ingress",
    }
    resp_raw = await client.post("/api/v1/ingest/raw", json=raw_payload, headers=auth_headers)
    assert resp_raw.status_code == 201
    data = resp_raw.json()
    assert "GET /api/v1/health - 200" in data["message"]
    assert data["service"] == "nginx-ingress"

    # Batch raw syslog lines
    batch_payload = {
        "lines": [
            "<34>Oct 11 22:14:15 server1 su: auth OK",
            "<34>Oct 11 22:14:16 server1 su: session opened",
        ],
        "format": "SYSLOG",
    }
    resp_batch = await client.post(
        "/api/v1/ingest/raw/batch",
        json=batch_payload,
        headers=auth_headers,
    )
    assert resp_batch.status_code == 201
    assert resp_batch.json()["ingested"] == 2
