"""Configurable regular expression log parser.

Extracts named capture groups into structured LogEntry fields.
"""

import re
from datetime import UTC, datetime
from typing import Any

from log_aggregator.exceptions import LogParsingError
from log_aggregator.models.log_entry import LogEntry, LogLevel
from log_aggregator.parsers.base import BaseLogParser

# Default standard application log format: YYYY-MM-DD HH:MM:SS [LEVEL] [service] message
DEFAULT_APP_LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+"
    r"\[?(?P<level>[A-Za-z]+)\]?\s+"
    r"(?:\[(?P<service>[A-Za-z0-9_\-\.]+)\]\s+)?"
    r"(?P<message>.*)$"
)


class RegexLogParser(BaseLogParser):
    """Regex-based parser supporting custom or standard application log patterns."""

    def __init__(self, pattern: str | re.Pattern[str] | None = None) -> None:
        """Initialize with an optional custom compiled pattern or regex string."""
        if pattern is None:
            self.pattern = DEFAULT_APP_LOG_PATTERN
        elif isinstance(pattern, str):
            self.pattern = re.compile(pattern)
        else:
            self.pattern = pattern

    def can_parse(self, raw: str) -> bool:
        """Check if raw line matches the configured regex pattern."""
        return bool(self.pattern.match(raw.strip()))

    def parse(
        self,
        raw: str,
        default_service: str = "default",
        source: str = "app",
    ) -> LogEntry:
        """Parse raw string using named capture groups."""
        stripped = raw.strip()
        match = self.pattern.match(stripped)
        if not match:
            raise LogParsingError(
                f"Line did not match pattern '{self.pattern.pattern}'", raw_line=raw
            )

        groups = match.groupdict()
        message = groups.pop("message", stripped) or stripped
        service = groups.pop("service", None) or default_service
        level_str = groups.pop("level", "INFO") or "INFO"
        level = LogLevel.from_string(level_str)

        # Parse timestamp if captured
        timestamp = datetime.now(UTC)
        if groups.get("timestamp"):
            ts_str = groups.pop("timestamp")
            timestamp = self._parse_timestamp(ts_str)

        # Remaining groups become metadata
        metadata: dict[str, Any] = {k: v for k, v in groups.items() if v is not None}

        return LogEntry(
            message=message,
            service=service,
            level=level,
            source=source,
            timestamp=timestamp,
            metadata=metadata,
            tags=["regex"],
            raw=raw,
        )

    def _parse_timestamp(self, ts_str: str) -> datetime:
        """Parse varied timestamp string representations."""
        # Replace space with T for ISO parsing
        normalized = ts_str.strip().replace(" ", "T")
        try:
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed
        except ValueError:
            return datetime.now(UTC)
