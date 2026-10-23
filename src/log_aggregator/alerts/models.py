"""Domain models for alerting rules and events.

Defines internal representation of alert rules, conditions, and trigger instances.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from log_aggregator.models.log_entry import LogLevel
from log_aggregator.schemas.alerts import AlertCondition


@dataclass
class AlertRule:
    """Configured rule specifying threshold conditions over a time window."""

    name: str
    condition: AlertCondition
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    service: str | None = None
    level: LogLevel | None = None
    pattern: str | None = None
    threshold: int = 5
    window_minutes: int = 1
    webhook_url: str | None = None
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_triggered_at: datetime | None = None


@dataclass
class AlertEvent:
    """Historical instance of a triggered alert rule."""

    rule_id: str
    rule_name: str
    message: str
    count: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    triggered_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, object]:
        """Convert alert event to a JSON-serializable dictionary."""
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "message": self.message,
            "count": self.count,
            "triggered_at": self.triggered_at.isoformat(),
        }
