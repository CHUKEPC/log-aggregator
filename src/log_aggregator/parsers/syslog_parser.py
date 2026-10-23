"""Syslog RFC 3164 and RFC 5424 log parser.

Parses BSD and IETF standard syslog messages into structured LogEntry records.
"""

import re
from datetime import UTC, datetime
from typing import Any

from log_aggregator.exceptions import LogParsingError
from log_aggregator.models.log_entry import LogEntry, LogLevel
from log_aggregator.parsers.base import BaseLogParser

# RFC 5424 regex: <PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID [SD] MSG
RFC5424_PATTERN = re.compile(
    r"^<(?P<pri>\d{1,3})>1\s+"
    r"(?P<timestamp>[^\s]+)\s+"
    r"(?P<hostname>[^\s]+)\s+"
    r"(?P<app_name>[^\s]+)\s+"
    r"(?P<proc_id>[^\s]+)\s+"
    r"(?P<msg_id>[^\s]+)\s*"
    r"(?P<rest>.*)$"
)

# RFC 3164 regex: <PRI>TIMESTAMP HOSTNAME TAG[PID]: MSG or TIMESTAMP HOSTNAME TAG[PID]: MSG
RFC3164_PATTERN = re.compile(
    r"^(?:<(?P<pri>\d{1,3})>)?"
    r"(?P<month>[A-Za-z]{3})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<hostname>[^\s:]+)\s+"
    r"(?P<tag>[a-zA-Z0-9_\-\./]+)(?:\[(?P<pid>\d+)\])?:\s+"
    r"(?P<message>.*)$"
)

SYSLOG_SEVERITY_MAP = {
    0: LogLevel.CRITICAL,  # Emergency
    1: LogLevel.CRITICAL,  # Alert
    2: LogLevel.CRITICAL,  # Critical
    3: LogLevel.ERROR,  # Error
    4: LogLevel.WARNING,  # Warning
    5: LogLevel.INFO,  # Notice
    6: LogLevel.INFO,  # Informational
    7: LogLevel.DEBUG,  # Debug
}


class SyslogParser(BaseLogParser):
    """Parser supporting both RFC 5424 and RFC 3164 Syslog messages."""

    def can_parse(self, raw: str) -> bool:
        """Check if message matches RFC 5424 or RFC 3164 regex pattern."""
        stripped = raw.strip()
        return bool(RFC5424_PATTERN.match(stripped) or RFC3164_PATTERN.match(stripped))

    def parse(
        self,
        raw: str,
        default_service: str = "default",
        source: str = "syslog",
    ) -> LogEntry:
        """Parse raw syslog line into LogEntry."""
        stripped = raw.strip()

        # Attempt RFC 5424 parsing
        m_5424 = RFC5424_PATTERN.match(stripped)
        if m_5424:
            return self._parse_rfc5424(m_5424, raw, default_service, source)

        # Attempt RFC 3164 parsing
        m_3164 = RFC3164_PATTERN.match(stripped)
        if m_3164:
            return self._parse_rfc3164(m_3164, raw, default_service, source)

        raise LogParsingError("Failed to parse syslog line", raw_line=raw)

    def _parse_rfc5424(
        self,
        match: re.Match[str],
        raw: str,
        default_service: str,
        source: str,
    ) -> LogEntry:
        """Parse RFC 5424 regex matches."""
        pri_str = match.group("pri")
        pri = int(pri_str)
        severity = pri % 8
        facility = pri // 8
        level = SYSLOG_SEVERITY_MAP.get(severity, LogLevel.INFO)

        ts_str = match.group("timestamp")
        timestamp = datetime.now(UTC)
        if ts_str and ts_str != "-":
            try:
                normalized = ts_str.replace("Z", "+00:00")
                parsed = datetime.fromisoformat(normalized)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
                timestamp = parsed
            except ValueError:
                pass

        hostname = match.group("hostname")
        if hostname == "-":
            hostname = source

        app_name = match.group("app_name")
        service = app_name if app_name and app_name != "-" else default_service

        proc_id = match.group("proc_id")
        msg_id = match.group("msg_id")
        rest = match.group("rest") or ""

        # Check for structured data in brackets
        sd_match = re.match(r"^(\[[^\]]+\])\s*(.*)$", rest)
        metadata: dict[str, Any] = {
            "facility": facility,
            "severity": severity,
            "hostname": hostname,
        }
        if proc_id != "-":
            metadata["proc_id"] = proc_id
        if msg_id != "-":
            metadata["msg_id"] = msg_id

        if sd_match:
            metadata["structured_data"] = sd_match.group(1)
            message = sd_match.group(2)
        else:
            message = rest

        return LogEntry(
            message=message.strip(),
            service=service,
            level=level,
            source=hostname,
            timestamp=timestamp,
            metadata=metadata,
            tags=["syslog", "rfc5424"],
            raw=raw,
        )

    def _parse_rfc3164(
        self,
        match: re.Match[str],
        raw: str,
        default_service: str,
        source: str,
    ) -> LogEntry:
        """Parse RFC 3164 regex matches."""
        pri_str = match.group("pri")
        metadata: dict[str, Any] = {}
        level = LogLevel.INFO

        if pri_str:
            pri = int(pri_str)
            severity = pri % 8
            facility = pri // 8
            level = SYSLOG_SEVERITY_MAP.get(severity, LogLevel.INFO)
            metadata["facility"] = facility
            metadata["severity"] = severity

        # Build approximate timestamp (syslog RFC 3164 lacks year, assume current year)
        month = match.group("month")
        day = int(match.group("day"))
        time_part = match.group("time")
        current_year = datetime.now(UTC).year
        try:
            ts_str = f"{current_year} {month} {day:02d} {time_part}"
            timestamp = datetime.strptime(ts_str, "%Y %b %d %H:%M:%S").replace(tzinfo=UTC)
        except ValueError:
            timestamp = datetime.now(UTC)

        hostname = match.group("hostname") or source
        tag = match.group("tag") or default_service
        pid = match.group("pid")
        if pid:
            metadata["pid"] = pid

        message = match.group("message")

        return LogEntry(
            message=message,
            service=tag,
            level=level,
            source=hostname,
            timestamp=timestamp,
            metadata=metadata,
            tags=["syslog", "rfc3164"],
            raw=raw,
        )
