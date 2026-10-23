"""API tests for alert rules configuration and events endpoints."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_alert_rules_crud_and_events(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    # 1. Create alert rule
    rule_payload = {
        "name": "Database Errors Alert",
        "condition": "ERROR_COUNT",
        "service": "db-service",
        "threshold": 3,
        "window_minutes": 2,
        "webhook_url": "https://example.com/webhook",
        "enabled": True,
    }

    create_resp = await client.post(
        "/api/v1/alerts/rules",
        json=rule_payload,
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    rule_data = create_resp.json()
    rule_id = rule_data["id"]
    assert rule_data["name"] == "Database Errors Alert"

    # 2. List alert rules
    list_resp = await client.get("/api/v1/alerts/rules", headers=auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # 3. Get single rule
    get_resp = await client.get(f"/api/v1/alerts/rules/{rule_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == rule_id

    # 4. List alert events
    events_resp = await client.get("/api/v1/alerts/events", headers=auth_headers)
    assert events_resp.status_code == 200
    assert isinstance(events_resp.json(), list)

    # 5. Delete rule
    del_resp = await client.delete(f"/api/v1/alerts/rules/{rule_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    # 6. Verify deletion
    verify_resp = await client.get(f"/api/v1/alerts/rules/{rule_id}", headers=auth_headers)
    assert verify_resp.status_code == 404
