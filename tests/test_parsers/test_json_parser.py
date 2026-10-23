"""Unit tests for JSON log parser."""

import json
from datetime import datetime

import pytest

from log_aggregator.exceptions import LogParsingError
from log_aggregator.models.log_entry import LogLevel
from log_aggregator.parsers.json_parser import JsonLogParser


def test_json_parser_can_parse() -> None:
    parser = JsonLogParser()
    assert parser.can_parse('{"message": "hello", "level": "INFO"}')
    assert parser.can_parse('  {"app": "worker"}  ')
    assert not parser.can_parse("Plain text log line")
    assert not parser.can_parse("{not valid json}")
    assert not parser.can_parse("12345")


def test_json_parser_standard_fields() -> None:
    parser = JsonLogParser()
    raw = json.dumps(
        {
            "message": "User checkout completed",
            "level": "INFO",
            "service": "checkout-service",
            "timestamp": "2023-11-05T14:30:00Z",
            "tags": ["ecommerce", "checkout"],
            "order_id": 9876,
            "amount": 49.99,
        }
    )

    entry = parser.parse(raw, default_service="default-svc", source="unit-test")

    assert entry.message == "User checkout completed"
    assert entry.level == LogLevel.INFO
    assert entry.service == "checkout-service"
    assert entry.source == "unit-test"
    assert entry.tags == ["ecommerce", "checkout"]
    assert entry.metadata["order_id"] == 9876
    assert entry.metadata["amount"] == 49.99
    assert entry.timestamp.year == 2023


def test_json_parser_field_aliases() -> None:
    parser = JsonLogParser()
    # Test msg, lvl, app, ts in milliseconds
    raw = json.dumps(
        {
            "msg": "Worker memory spike",
            "lvl": "WARN",
            "app": "celery-worker",
            "ts": 1699194600000,  # millisecond epoch
            "cluster": "eu-west-1",
        }
    )

    entry = parser.parse(raw)
    assert entry.message == "Worker memory spike"
    assert entry.level == LogLevel.WARNING
    assert entry.service == "celery-worker"
    assert entry.metadata["cluster"] == "eu-west-1"
    assert isinstance(entry.timestamp, datetime)


def test_json_parser_fallback_message_and_invalid_json() -> None:
    parser = JsonLogParser()
    # No message key present
    raw = json.dumps({"status": "200", "duration_ms": 12})
    entry = parser.parse(raw, default_service="api")
    assert entry.service == "api"
    assert "status" in entry.message or "200" in entry.message

    # Invalid JSON raises LogParsingError
    with pytest.raises(LogParsingError):
        parser.parse("{bad json line")
