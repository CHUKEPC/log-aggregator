"""Unit tests for Syslog RFC 5424 and RFC 3164 parser."""

import pytest

from log_aggregator.exceptions import LogParsingError
from log_aggregator.models.log_entry import LogLevel
from log_aggregator.parsers.syslog_parser import SyslogParser


def test_syslog_rfc5424_parsing() -> None:
    parser = SyslogParser()
    raw = (
        "<165>1 2023-10-11T22:14:15.003Z mymachine.example.com evntslog 1234 ID47 "
        '[exampleSDID@32473 iut="3"] User authorization failure'
    )

    assert parser.can_parse(raw)
    entry = parser.parse(raw)

    assert entry.message == "User authorization failure"
    assert entry.service == "evntslog"
    assert entry.source == "mymachine.example.com"
    # PRI 165: 165 % 8 = 5 (Notice -> INFO)
    assert entry.level == LogLevel.INFO
    assert "rfc5424" in entry.tags
    assert entry.metadata["proc_id"] == "1234"
    assert entry.metadata["msg_id"] == "ID47"
    assert "[exampleSDID@32473" in entry.metadata["structured_data"]


def test_syslog_rfc3164_parsing() -> None:
    parser = SyslogParser()
    raw = "<34>Oct 11 22:14:15 server1 su[4321]: 'su root' failed for user test on /dev/pts/1"

    assert parser.can_parse(raw)
    entry = parser.parse(raw)

    assert entry.message == "'su root' failed for user test on /dev/pts/1"
    assert entry.service == "su"
    assert entry.source == "server1"
    # PRI 34: 34 % 8 = 2 (Critical -> CRITICAL)
    assert entry.level == LogLevel.CRITICAL
    assert entry.metadata["pid"] == "4321"
    assert "rfc3164" in entry.tags


def test_syslog_rfc3164_without_pri() -> None:
    parser = SyslogParser()
    raw = "Oct 11 22:14:15 webserver nginx[999]: Configuration reloaded successfully"

    assert parser.can_parse(raw)
    entry = parser.parse(raw)
    assert entry.message == "Configuration reloaded successfully"
    assert entry.service == "nginx"
    assert entry.source == "webserver"
    assert entry.metadata["pid"] == "999"


def test_syslog_invalid_line() -> None:
    parser = SyslogParser()
    assert not parser.can_parse("invalid random text that does not look like syslog")
    with pytest.raises(LogParsingError):
        parser.parse("invalid random text")
