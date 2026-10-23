"""Unit tests for regular expression log parser."""

import pytest

from log_aggregator.exceptions import LogParsingError
from log_aggregator.models.log_entry import LogLevel
from log_aggregator.parsers.regex_parser import RegexLogParser


def test_regex_parser_default_format() -> None:
    parser = RegexLogParser()
    raw = "2023-11-01 10:20:30 [ERROR] [payment-gateway] Connection refused by remote host"

    assert parser.can_parse(raw)
    entry = parser.parse(raw)

    assert entry.message == "Connection refused by remote host"
    assert entry.service == "payment-gateway"
    assert entry.level == LogLevel.ERROR
    assert entry.timestamp.year == 2023


def test_regex_parser_custom_pattern() -> None:
    # Custom format: LEVEL | SERVICE | MESSAGE
    custom_pattern = r"^(?P<level>[A-Z]+)\s*\|\s*(?P<service>[\w-]+)\s*\|\s*(?P<message>.*)$"
    parser = RegexLogParser(pattern=custom_pattern)
    raw = "WARNING | auth-service | Token expiration threshold reached"

    assert parser.can_parse(raw)
    entry = parser.parse(raw)

    assert entry.level == LogLevel.WARNING
    assert entry.service == "auth-service"
    assert entry.message == "Token expiration threshold reached"


def test_regex_parser_non_matching_line() -> None:
    custom_pattern = r"^CRITICAL\s+ALERT:\s+(?P<message>.*)$"
    parser = RegexLogParser(pattern=custom_pattern)
    assert not parser.can_parse("INFO simple message")
    with pytest.raises(LogParsingError):
        parser.parse("INFO simple message")
