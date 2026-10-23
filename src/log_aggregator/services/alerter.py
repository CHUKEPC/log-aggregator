"""Service layer for alert rules and triggered event notifications.

Coordinates alert configuration and querying historical alert events.
"""

from log_aggregator.alerts.evaluator import AlertEvaluator
from log_aggregator.alerts.models import AlertEvent, AlertRule
from log_aggregator.alerts.notifier import AlertNotifier
from log_aggregator.exceptions import NotFoundError
from log_aggregator.schemas.alerts import AlertRuleCreate


class AlertService:
    """Business logic for configuring alert rules and reviewing triggered events."""

    def __init__(self, evaluator: AlertEvaluator, notifier: AlertNotifier) -> None:
        """Initialize with alert evaluator and notifier instances."""
        self.evaluator = evaluator
        self.notifier = notifier

    def create_rule(self, rule_in: AlertRuleCreate) -> AlertRule:
        """Create and register a new alert rule."""
        rule = AlertRule(
            name=rule_in.name,
            condition=rule_in.condition,
            service=rule_in.service,
            level=rule_in.level,
            pattern=rule_in.pattern,
            threshold=rule_in.threshold,
            window_minutes=rule_in.window_minutes,
            webhook_url=rule_in.webhook_url,
            enabled=rule_in.enabled,
        )
        self.evaluator.add_rule(rule)
        return rule

    def list_rules(self) -> list[AlertRule]:
        """List all configured alert rules."""
        return self.evaluator.get_rules()

    def get_rule(self, rule_id: str) -> AlertRule:
        """Retrieve an alert rule by ID or raise NotFoundError."""
        rule = self.evaluator.get_rule(rule_id)
        if not rule:
            raise NotFoundError(f"Alert rule '{rule_id}' not found")
        return rule

    def delete_rule(self, rule_id: str) -> None:
        """Delete an alert rule or raise NotFoundError."""
        deleted = self.evaluator.remove_rule(rule_id)
        if not deleted:
            raise NotFoundError(f"Alert rule '{rule_id}' not found")

    def list_events(self, limit: int = 50) -> list[AlertEvent]:
        """List recently triggered alert events."""
        return self.notifier.get_events(limit=limit)
