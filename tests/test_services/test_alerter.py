"""Unit tests for AlertService."""

import pytest

from log_aggregator.exceptions import NotFoundError
from log_aggregator.schemas.alerts import AlertCondition, AlertRuleCreate
from log_aggregator.services.alerter import AlertService


def test_alerter_service_crud(alerter: AlertService) -> None:
    rule_create = AlertRuleCreate(
        name="CPU Alert",
        condition=AlertCondition.ERROR_COUNT,
        service="worker",
        threshold=5,
        window_minutes=2,
    )
    rule = alerter.create_rule(rule_create)
    assert rule.id is not None
    assert rule.name == "CPU Alert"

    # List rules
    rules = alerter.list_rules()
    assert len(rules) >= 1

    # Get rule
    found = alerter.get_rule(rule.id)
    assert found.name == "CPU Alert"

    # Delete rule
    alerter.delete_rule(rule.id)
    with pytest.raises(NotFoundError):
        alerter.get_rule(rule.id)

    # Delete non-existent raises NotFoundError
    with pytest.raises(NotFoundError):
        alerter.delete_rule("unknown-rule")
