"""Unit tests for Nginx access and error log parser."""

import pytest

from log_aggregator.exceptions import LogParsingError
from log_aggregator.models.log_entry import LogLevel
from log_aggregator.parsers.nginx_parser import NginxLogParser


def test_nginx_access_log_parsing() -> None:
    parser = NginxLogParser()
    raw = (
        "192.168.1.50 - frank [10/Oct/2023:13:55:36 +0000] "
        '"GET /api/v1/orders?status=active HTTP/1.1" 200 2326 '
        '"https://example.com/dashboard" "Mozilla/5.0 (Macintosh)"'
    )

    assert parser.can_parse(raw)
    entry = parser.parse(raw)

    assert "GET /api/v1/orders?status=active - 200" in entry.message
    assert entry.service == "nginx"
    assert entry.level == LogLevel.INFO
    assert entry.metadata["client_ip"] == "192.168.1.50"
    assert entry.metadata["status_code"] == 200
    assert entry.metadata["bytes_sent"] == 2326
    assert entry.metadata["method"] == "GET"
    assert entry.metadata["path"] == "/api/v1/orders?status=active"
    assert entry.metadata["referer"] == "https://example.com/dashboard"
    assert "access" in entry.tags


def test_nginx_access_error_status_mapping() -> None:
    parser = NginxLogParser()
    # 502 Bad Gateway should map to LogLevel.ERROR
    raw_502 = (
        '10.0.0.1 - - [10/Oct/2023:13:55:36 +0000] "POST /api/v1/payment HTTP/1.1" 502 0 "-" "-"'
    )
    entry_502 = parser.parse(raw_502)
    assert entry_502.level == LogLevel.ERROR

    # 404 Not Found should map to LogLevel.WARNING
    raw_404 = '10.0.0.1 - - [10/Oct/2023:13:55:36 +0000] "GET /unknown HTTP/1.1" 404 150 "-" "-"'
    entry_404 = parser.parse(raw_404)
    assert entry_404.level == LogLevel.WARNING


def test_nginx_error_log_parsing() -> None:
    parser = NginxLogParser()
    raw = (
        '2023/10/10 13:55:36 [error] 1234#5678: *1 open() "/usr/share/nginx/html/missing.html" '
        "failed (2: No such file or directory), client: 192.168.1.1"
    )

    assert parser.can_parse(raw)
    entry = parser.parse(raw)

    assert 'open() "/usr/share/nginx/html/missing.html" failed' in entry.message
    assert entry.level == LogLevel.ERROR
    assert entry.metadata["pid"] == 1234
    assert entry.metadata["tid"] == 5678
    assert "error" in entry.tags


def test_nginx_invalid_line() -> None:
    parser = NginxLogParser()
    assert not parser.can_parse("just a random string")
    with pytest.raises(LogParsingError):
        parser.parse("just a random string")
