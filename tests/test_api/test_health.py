"""API tests for service health endpoint."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_health_check(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "environment" in data
    assert data["storage_healthy"] is True
