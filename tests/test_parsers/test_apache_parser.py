"""Unit tests for Apache web server log parser."""

import pytest

from log_aggregator.exceptions import LogParsingError
from log_aggregator.models.log_entry import LogLevel
from log_aggregator.parsers.apache_parser import ApacheLogParser


def test_apache_combined_parsing() -> None:
    parser = ApacheLogParser()
    raw = (
        "127.0.0.1 - frank [10/Oct/2023:13:55:36 -0700] "
        '"GET /apache_pb.gif HTTP/1.0" 200 2326 '
        '"http://www.example.com/start.html" "Mozilla/4.08 [en] (Win98; I ;Nav)"'
    )

    assert parser.can_parse(raw)
    entry = parser.parse(raw)

    assert "GET /apache_pb.gif - 200" in entry.message
    assert entry.service == "apache"
    assert entry.level == LogLevel.INFO
    assert entry.metadata["client_ip"] == "127.0.0.1"
    assert entry.metadata["auth_user"] == "frank"
    assert entry.metadata["status_code"] == 200
    assert entry.metadata["bytes_sent"] == 2326
    assert entry.metadata["referer"] == "http://www.example.com/start.html"
    assert "apache" in entry.tags


def test_apache_server_error_mapping() -> None:
    parser = ApacheLogParser()
    raw = '127.0.0.1 - - [10/Oct/2023:13:55:36 -0700] "GET /crash HTTP/1.0" 500 512 "-" "-"'
    entry = parser.parse(raw)
    assert entry.level == LogLevel.ERROR


def test_apache_invalid_line() -> None:
    parser = ApacheLogParser()
    assert not parser.can_parse("not an apache line")
    with pytest.raises(LogParsingError):
        parser.parse("not an apache line")
