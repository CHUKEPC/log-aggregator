"""Alert evaluation engine.

Monitors incoming log streams within a sliding time window and triggers alerts
when configured thresholds or patterns are breached.
"""

import logging
import re
from collections import deque
from datetime import UTC, datetime, timedelta

from log_aggregator.alerts.models import AlertEvent, AlertRule
from log_aggregator.models.log_entry import LogEntry, LogLevel
from log_aggregator.schemas.alerts import AlertCondition

logger = logging.getLogger(__name__)


class AlertEvaluator:
    """Evaluates configured alert rules against a sliding window of recent log entries."""

    def __init__(self, max_window_minutes: int = 60, cooldown_seconds: int = 30) -> None:
        """Initialize sliding log buffer and rule list."""
        self.max_window_minutes = max_window_minutes
        self.cooldown_seconds = cooldown_seconds
        self._rules: dict[str, AlertRule] = {}
        # Stores tuples of (entry_timestamp_utc, LogEntry)
        self._buffer: deque[tuple[datetime, LogEntry]] = deque()

    def add_rule(self, rule: AlertRule) -> None:
        """Register or update an alert rule."""
        self._rules[rule.id] = rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule by ID."""
        return bool(self._rules.pop(rule_id, None))

    def get_rules(self) -> list[AlertRule]:
        """Return list of all configured rules."""
        return list(self._rules.values())

    def get_rule(self, rule_id: str) -> AlertRule | None:
        """Find a rule by ID."""
        return self._rules.get(rule_id)

    def evaluate(self, new_entries: list[LogEntry]) -> list[AlertEvent]:
        """Ingest new log entries, prune stale window buffer, and evaluate active rules."""
        now = datetime.now(UTC)

        # Buffer new entries
        for entry in new_entries:
            ts = entry.timestamp if entry.timestamp.tzinfo else entry.timestamp.replace(tzinfo=UTC)
            self._buffer.append((ts, entry))

        # Prune records older than maximum sliding window
        cutoff = now - timedelta(minutes=self.max_window_minutes)
        while self._buffer and self._buffer[0][0] < cutoff:
            self._buffer.popleft()

        triggered_events: list[AlertEvent] = []

        # Evaluate all enabled rules
        for rule in self._rules.values():
            if not rule.enabled:
                continue

            # Respect cooldown to prevent spamming
            if rule.last_triggered_at:
                elapsed = (now - rule.last_triggered_at).total_seconds()
                if elapsed < self.cooldown_seconds:
                    continue

            rule_cutoff = now - timedelta(minutes=rule.window_minutes)
            matching_count = 0

            # Count logs matching the rule within the rule's specific window
            for log_ts, entry in self._buffer:
                if log_ts < rule_cutoff:
                    continue
                if self._matches_rule_criteria(entry, rule):
                    matching_count += 1

            if matching_count >= rule.threshold:
                rule.last_triggered_at = now
                event = AlertEvent(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    count=matching_count,
                    triggered_at=now,
                    message=(
                        f"Rule '{rule.name}' triggered: condition {rule.condition.value} reached "
                        f"{matching_count} occurrences in {rule.window_minutes}m (threshold: {rule.threshold})"
                    ),
                )
                triggered_events.append(event)
                logger.warning("Alert triggered: %s", event.message)

        return triggered_events

    def _matches_rule_criteria(self, entry: LogEntry, rule: AlertRule) -> bool:
        """Check if an individual log entry matches the criteria for a rule."""
        if rule.service and entry.service != rule.service:
            return False

        if rule.condition == AlertCondition.ERROR_COUNT:
            # Matches error or critical levels, or specified level
            target_level = rule.level or LogLevel.ERROR
            if target_level == LogLevel.ERROR:
                if entry.level not in (LogLevel.ERROR, LogLevel.CRITICAL):
                    return False
            elif entry.level != target_level:
                return False

            if rule.pattern:
                return self._matches_pattern(entry.message, rule.pattern)
            return True

        if rule.condition == AlertCondition.KEYWORD_MATCH:
            if rule.level and entry.level != rule.level:
                return False
            if rule.pattern:
                return self._matches_pattern(entry.message, rule.pattern)
            return True

        if rule.condition == AlertCondition.LOG_RATE:
            if rule.level and entry.level != rule.level:
                return False
            if rule.pattern:
                return self._matches_pattern(entry.message, rule.pattern)
            return True

        return False

    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Check regex or substring match."""
        try:
            return bool(re.search(pattern, text, re.IGNORECASE))
        except re.error:
            return pattern.lower() in text.lower()
