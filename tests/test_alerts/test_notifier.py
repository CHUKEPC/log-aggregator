"""Unit tests for AlertNotifier."""

from unittest.mock import AsyncMock

import httpx
import pytest

from log_aggregator.alerts.models import AlertEvent, AlertRule
from log_aggregator.alerts.notifier import AlertNotifier
from log_aggregator.schemas.alerts import AlertCondition


@pytest.mark.asyncio
async def test_notifier_webhook_dispatch() -> None:
    notifier = AlertNotifier(history_limit=50)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.is_closed = False
    mock_resp = httpx.Response(status_code=200)
    mock_client.post.return_value = mock_resp
    notifier._http_client = mock_client

    rule = AlertRule(
        name="Webhook Test",
        condition=AlertCondition.ERROR_COUNT,
        webhook_url="https://alerts.example.com/webhook",
        threshold=5,
    )
    event = AlertEvent(
        rule_id=rule.id,
        rule_name=rule.name,
        message="5 errors observed",
        count=5,
    )

    await notifier.notify(rule, event)

    # Allow background task to complete
    if notifier._background_tasks:
        import asyncio

        await asyncio.gather(*notifier._background_tasks)

    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert call_args[0][0] == "https://alerts.example.com/webhook"
    assert call_args[1]["json"]["rule_name"] == "Webhook Test"

    # Verify event stored in history
    events = notifier.get_events(limit=10)
    assert len(events) == 1
    assert events[0].id == event.id


@pytest.mark.asyncio
async def test_notifier_no_webhook_url() -> None:
    notifier = AlertNotifier()
    rule = AlertRule(name="Internal Only", condition=AlertCondition.LOG_RATE, webhook_url=None)
    event = AlertEvent(rule_id=rule.id, rule_name=rule.name, message="msg", count=1)

    await notifier.notify(rule, event)
    events = notifier.get_events()
    assert len(events) == 1
    assert events[0].rule_name == "Internal Only"
