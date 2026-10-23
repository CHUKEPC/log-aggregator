"""Apache web server log parser.

Parses Apache Common Log Format (CLF) and Combined Log Format entries.
"""

import re
from datetime import UTC, datetime
from typing import Any

from log_aggregator.exceptions import LogParsingError
from log_aggregator.models.log_entry import LogEntry, LogLevel
from log_aggregator.parsers.base import BaseLogParser

# Apache Combined/Common Log Format: IP IDENT AUTH [TIME] "REQ" STATUS BYTES ["REF" "UA"]
APACHE_PATTERN = re.compile(
    r'^(?P<ip>[^\s]+)\s+(?P<ident>[^\s]+)\s+(?P<auth>[^\s]+)\s+\[(?P<time>[^\]]+)\]\s+"(?P<request>[^"]+)"\s+'
    r'(?P<status>\d{3})\s+(?P<bytes>\d+|-)(?:\s+"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)")?'
)


class ApacheLogParser(BaseLogParser):
    """Parser for Apache CLF and Combined log entries."""

    def can_parse(self, raw: str) -> bool:
        """Check if raw line matches Apache log format."""
        return bool(APACHE_PATTERN.match(raw.strip()))

    def parse(
        self,
        raw: str,
        default_service: str = "apache",
        source: str = "web",
    ) -> LogEntry:
        """Parse Apache log line into LogEntry."""
        stripped = raw.strip()
        match = APACHE_PATTERN.match(stripped)
        if not match:
            raise LogParsingError("Failed to parse Apache log line", raw_line=raw)

        ip = match.group("ip")
        auth = match.group("auth")
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

        try:
            timestamp = datetime.strptime(time_str, "%d/%b/%Y:%H:%M:%S %z")
        except ValueError:
            timestamp = datetime.now(UTC)

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
        if auth != "-":
            metadata["auth_user"] = auth

        return LogEntry(
            message=f"{method} {path} - {status_code}",
            service=default_service,
            level=level,
            source=source,
            timestamp=timestamp,
            metadata=metadata,
            tags=["apache", "access"],
            raw=raw,
        )
