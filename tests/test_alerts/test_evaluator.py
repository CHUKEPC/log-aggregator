"""Unit tests for AlertEvaluator engine."""

from datetime import UTC, datetime, timedelta

from log_aggregator.alerts.evaluator import AlertEvaluator
from log_aggregator.alerts.models import AlertRule
from log_aggregator.models.log_entry import LogEntry, LogLevel
from log_aggregator.schemas.alerts import AlertCondition


def test_evaluator_error_count_threshold() -> None:
    evaluator = AlertEvaluator(max_window_minutes=5, cooldown_seconds=0)
    rule = AlertRule(
        name="High Error Rate",
        condition=AlertCondition.ERROR_COUNT,
        service="payment-service",
        threshold=3,
        window_minutes=2,
    )
    evaluator.add_rule(rule)

    entries = [
        LogEntry(message="Error 1", service="payment-service", level=LogLevel.ERROR),
        LogEntry(message="Error 2", service="payment-service", level=LogLevel.ERROR),
    ]
    # 2 errors < threshold 3 -> no events
    events = evaluator.evaluate(entries)
    assert len(events) == 0

    # Add 3rd error -> triggers alert
    third_entry = [LogEntry(message="Error 3", service="payment-service", level=LogLevel.ERROR)]
    events = evaluator.evaluate(third_entry)
    assert len(events) == 1
    assert events[0].rule_name == "High Error Rate"
    assert events[0].count == 3


def test_evaluator_keyword_match() -> None:
    evaluator = AlertEvaluator(max_window_minutes=5, cooldown_seconds=0)
    rule = AlertRule(
        name="OOM Detection",
        condition=AlertCondition.KEYWORD_MATCH,
        pattern=r"Out of memory|OOMKilled",
        threshold=2,
        window_minutes=1,
    )
    evaluator.add_rule(rule)

    entries = [
        LogEntry(message="Task killed by Out of memory killer", service="worker"),
        LogEntry(message="Container OOMKilled detected", service="infra"),
    ]
    events = evaluator.evaluate(entries)
    assert len(events) == 1
    assert events[0].rule_name == "OOM Detection"


def test_evaluator_disabled_rule() -> None:
    evaluator = AlertEvaluator(max_window_minutes=5, cooldown_seconds=0)
    rule = AlertRule(
        name="Disabled Rule",
        condition=AlertCondition.LOG_RATE,
        threshold=1,
        window_minutes=1,
        enabled=False,
    )
    evaluator.add_rule(rule)

    entries = [LogEntry(message="Any log", service="api")]
    events = evaluator.evaluate(entries)
    assert len(events) == 0


def test_evaluator_window_pruning() -> None:
    evaluator = AlertEvaluator(max_window_minutes=1, cooldown_seconds=0)
    rule = AlertRule(
        name="Rate Rule",
        condition=AlertCondition.LOG_RATE,
        threshold=2,
        window_minutes=1,
    )
    evaluator.add_rule(rule)

    old_time = datetime.now(UTC) - timedelta(minutes=10)
    old_entries = [
        LogEntry(message="Old log 1", service="api", timestamp=old_time),
        LogEntry(message="Old log 2", service="api", timestamp=old_time),
    ]
    evaluator.evaluate(old_entries)

    # Now evaluate with 1 recent log -> should not trigger because old logs are out of window
    recent_entry = [LogEntry(message="Recent log", service="api")]
    events = evaluator.evaluate(recent_entry)
    assert len(events) == 0
