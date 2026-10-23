"""JSON format log parser.

Extracts standard logging fields from arbitrary JSON payloads, retaining all
extra attributes within metadata.
"""

import json
from datetime import UTC, datetime
from typing import Any

from log_aggregator.exceptions import LogParsingError
from log_aggregator.models.log_entry import LogEntry, LogLevel
from log_aggregator.parsers.base import BaseLogParser


class JsonLogParser(BaseLogParser):
    """Parser for JSON-formatted structured log lines."""

    def can_parse(self, raw: str) -> bool:
        """Check if string begins and ends with JSON object delimiters."""
        stripped = raw.strip()
        if not (stripped.startswith("{") and stripped.endswith("}")):
            return False
        try:
            parsed = json.loads(stripped)
            return isinstance(parsed, dict)
        except Exception:
            return False

    def parse(
        self,
        raw: str,
        default_service: str = "default",
        source: str = "raw",
    ) -> LogEntry:
        """Parse JSON text into LogEntry."""
        stripped = raw.strip()
        try:
            data: dict[str, Any] = json.loads(stripped)
        except Exception as exc:
            raise LogParsingError(f"Invalid JSON format: {exc}", raw_line=raw) from exc

        # Extract message from common aliases
        message = ""
        for msg_key in ("message", "msg", "log", "text", "content"):
            if msg_key in data:
                message = str(data.pop(msg_key))
                break
        if not message:
            message = stripped

        # Extract severity level from common aliases
        level_val = "INFO"
        for lvl_key in ("level", "lvl", "severity", "log_level", "status"):
            if lvl_key in data:
                level_val = str(data.pop(lvl_key))
                break
        level = LogLevel.from_string(level_val)

        # Extract service identifier
        service = default_service
        for s_key in ("service", "app", "application", "service_name"):
            if s_key in data:
                service = str(data.pop(s_key))
                break

        # Extract or infer timestamp
        timestamp = datetime.now(UTC)
        for ts_key in ("timestamp", "ts", "@timestamp", "time", "datetime"):
            if ts_key in data:
                raw_ts = data.pop(ts_key)
                timestamp = self._parse_timestamp(raw_ts)
                break

        # Extract tags if given as list
        tags: list[str] = []
        if "tags" in data and isinstance(data["tags"], list):
            tags = [str(t) for t in data.pop("tags")]

        # Any remaining attributes are preserved as structured metadata
        return LogEntry(
            message=message,
            service=service,
            level=level,
            source=source,
            timestamp=timestamp,
            metadata=data,
            tags=tags,
            raw=raw,
        )

    def _parse_timestamp(self, value: Any) -> datetime:
        """Convert float epoch, integer epoch, or ISO-8601 string to datetime."""
        if isinstance(value, (int, float)):
            # Distinguish milliseconds vs seconds timestamp
            if value > 1e11:
                return datetime.fromtimestamp(value / 1000.0, tz=UTC)
            return datetime.fromtimestamp(value, tz=UTC)
        if isinstance(value, str):
            try:
                # Handle 'Z' suffix replacing with '+00:00' for compatibility
                normalized = value.replace("Z", "+00:00")
                parsed = datetime.fromisoformat(normalized)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
                return parsed
            except ValueError:
                pass
        return datetime.now(UTC)
