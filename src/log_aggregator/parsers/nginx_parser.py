"""Nginx access and error log parser.

Parses Nginx combined access log lines and standard error log messages.
"""

import re
from datetime import UTC, datetime
from typing import Any

from log_aggregator.exceptions import LogParsingError
from log_aggregator.models.log_entry import LogEntry, LogLevel
from log_aggregator.parsers.base import BaseLogParser

# Nginx combined log format: $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"
NGINX_ACCESS_PATTERN = re.compile(
    r'^(?P<ip>[^\s]+)\s+-\s+(?P<user>[^\s]+)\s+\[(?P<time>[^\]]+)\]\s+"(?P<request>[^"]+)"\s+'
    r'(?P<status>\d{3})\s+(?P<bytes>\d+|-)(?:\s+"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)")?'
)

# Nginx error log: YYYY/MM/DD HH:MM:SS [level] pid#tid: *cid message
NGINX_ERROR_PATTERN = re.compile(
    r"^(?P<time>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})\s+\[(?P<level>\w+)\]\s+(?P<pid>\d+)#(?P<tid>\d+):\s+(?P<message>.*)$"
)


class NginxLogParser(BaseLogParser):
    """Parser for Nginx web server access and error logs."""

    def can_parse(self, raw: str) -> bool:
        """Check if raw line conforms to Nginx access or error patterns."""
        stripped = raw.strip()
        return bool(NGINX_ACCESS_PATTERN.match(stripped) or NGINX_ERROR_PATTERN.match(stripped))

    def parse(
        self,
        raw: str,
        default_service: str = "nginx",
        source: str = "web",
    ) -> LogEntry:
        """Parse Nginx access or error log line."""
        stripped = raw.strip()

        # Try access log format
        m_access = NGINX_ACCESS_PATTERN.match(stripped)
        if m_access:
            return self._parse_access_log(m_access, raw, default_service, source)

        # Try error log format
        m_error = NGINX_ERROR_PATTERN.match(stripped)
        if m_error:
            return self._parse_error_log(m_error, raw, default_service, source)

        raise LogParsingError("Failed to parse Nginx log line", raw_line=raw)

    def _parse_access_log(
        self,
        match: re.Match[str],
        raw: str,
        default_service: str,
        source: str,
    ) -> LogEntry:
        """Parse Nginx combined access log."""
        ip = match.group("ip")
        user = match.group("user")
        time_str = match.group("time")
        request = match.group("request")
        status_code = int(match.group("status"))
        bytes_sent = match.group("bytes")
        referer = match.group("referer") or ""
        user_agent = match.group("user_agent") or ""

        # Map HTTP status codes to LogLevel
        if status_code >= 500:
            level = LogLevel.ERROR
        elif status_code >= 400:
            level = LogLevel.WARNING
        else:
            level = LogLevel.INFO

        # Parse Nginx access log timestamp (e.g. 10/Oct/2023:13:55:36 +0000)
        try:
            timestamp = datetime.strptime(time_str, "%d/%b/%Y:%H:%M:%S %z")
        except ValueError:
            timestamp = datetime.now(UTC)

        # Parse HTTP method and path if possible
        req_parts = request.split()
        method = req_parts[0] if req_parts else ""
        path = req_parts[1] if len(req_parts) > 1 else ""

        metadata: dict[str, Any] = {
            "client_ip": ip,
            "status_code": status_code,
            "bytes_sent": int(bytes_sent) if bytes_sent != "-" else 0,
            "request": request,
            "method": method,
            "path": path,
            "referer": referer,
            "user_agent": user_agent,
        }
        if user != "-":
            metadata["user"] = user

        return LogEntry(
            message=f"{method} {path} - {status_code}",
            service=default_service,
            level=level,
            source=source,
            timestamp=timestamp,
            metadata=metadata,
            tags=["nginx", "access"],
            raw=raw,
        )

    def _parse_error_log(
        self,
        match: re.Match[str],
        raw: str,
        default_service: str,
        source: str,
    ) -> LogEntry:
        """Parse Nginx error log."""
        time_str = match.group("time")
        level_str = match.group("level")
        pid = match.group("pid")
        tid = match.group("tid")
        message = match.group("message")

        try:
            timestamp = datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S").replace(tzinfo=UTC)
        except ValueError:
            timestamp = datetime.now(UTC)

        level = LogLevel.from_string(level_str)

        metadata: dict[str, Any] = {
            "pid": int(pid),
            "tid": int(tid),
        }

        return LogEntry(
            message=message,
            service=default_service,
            level=level,
            source=source,
            timestamp=timestamp,
            metadata=metadata,
            tags=["nginx", "error"],
            raw=raw,
        )
