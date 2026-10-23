"""Unit tests for parser factory and auto-detection."""

from log_aggregator.models.log_entry import LogFormat, LogLevel
from log_aggregator.parsers.apache_parser import ApacheLogParser
from log_aggregator.parsers.factory import (
    auto_detect_parser,
    get_parser,
    parse_raw_line,
)
from log_aggregator.parsers.json_parser import JsonLogParser
from log_aggregator.parsers.nginx_parser import NginxLogParser
from log_aggregator.parsers.regex_parser import RegexLogParser
from log_aggregator.parsers.syslog_parser import SyslogParser


def test_get_parser() -> None:
    assert isinstance(get_parser(LogFormat.JSON), JsonLogParser)
    assert isinstance(get_parser(LogFormat.SYSLOG), SyslogParser)
    assert isinstance(get_parser(LogFormat.NGINX), NginxLogParser)
    assert isinstance(get_parser(LogFormat.APACHE), ApacheLogParser)
    assert isinstance(get_parser(LogFormat.REGEX), RegexLogParser)


def test_auto_detect_parser() -> None:
    json_line = '{"message": "test", "level": "INFO"}'
    assert isinstance(auto_detect_parser(json_line), JsonLogParser)

    syslog_line = "<34>Oct 11 22:14:15 server1 su: session opened"
    assert isinstance(auto_detect_parser(syslog_line), SyslogParser)

    nginx_line = '192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET / HTTP/1.1" 200 123 "-" "-"'
    # Both Nginx and Apache can parse Combined format
    detected = auto_detect_parser(nginx_line)
    assert isinstance(detected, (NginxLogParser, ApacheLogParser))

    regex_line = "2023-10-10 12:00:00 [DEBUG] [my-app] system starting"
    assert isinstance(auto_detect_parser(regex_line), RegexLogParser)


def test_parse_raw_line() -> None:
    entry = parse_raw_line(
        raw='{"msg": "Database query completed", "service": "db-proxy"}',
        default_service="fallback",
    )
    assert entry.message == "Database query completed"
    assert entry.service == "db-proxy"

    # Explicit format test
    raw_regex = "2023-10-10 12:00:00 [ERROR] [auth] Invalid credentials"
    entry_regex = parse_raw_line(raw=raw_regex, explicit_format=LogFormat.REGEX)
    assert entry_regex.level == LogLevel.ERROR
    assert entry_regex.service == "auth"
