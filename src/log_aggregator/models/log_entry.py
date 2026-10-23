"""Domain models for log records, search filters, and aggregations.

These entities represent core domain concepts decoupled from transport formats.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class LogLevel(StrEnum):
    """Standard logging severity levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_string(cls, value: str) -> "LogLevel":
        """Convert any case string or integer representation into LogLevel."""
        normalized = value.strip().upper()
        # Handle common abbreviations and aliases
        aliases = {
            "WARN": cls.WARNING,
            "ERR": cls.ERROR,
            "FATAL": cls.CRITICAL,
            "CRIT": cls.CRITICAL,
            "TRACE": cls.DEBUG,
        }
        if normalized in aliases:
            return aliases[normalized]
        try:
            return cls(normalized)
        except ValueError:
            return cls.INFO


class LogFormat(StrEnum):
    """Supported raw log formats for parsing."""

    JSON = "JSON"
    SYSLOG = "SYSLOG"
    NGINX = "NGINX"
    APACHE = "APACHE"
    REGEX = "REGEX"
    CUSTOM = "CUSTOM"


@dataclass
class LogEntry:
    """Core domain model representing a structured log document."""

    message: str
    service: str
    level: LogLevel = LogLevel.INFO
    source: str = "api"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    raw: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert log entry into a dictionary suitable for storage or serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "service": self.service,
            "message": self.message,
            "source": self.source,
            "metadata": self.metadata,
            "tags": self.tags,
            "raw": self.raw,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LogEntry":
        """Reconstruct a LogEntry from a dictionary representation."""
        ts_raw = data.get("timestamp")
        if isinstance(ts_raw, str):
            ts = datetime.fromisoformat(ts_raw)
        elif isinstance(ts_raw, datetime):
            ts = ts_raw
        else:
            ts = datetime.now(UTC)

        level_raw = data.get("level", "INFO")
        level = LogLevel.from_string(str(level_raw))

        return cls(
            id=str(data.get("id", uuid.uuid4())),
            timestamp=ts,
            level=level,
            service=str(data.get("service", "unknown")),
            message=str(data.get("message", "")),
            source=str(data.get("source", "system")),
            metadata=dict(data.get("metadata") or {}),
            tags=list(data.get("tags") or []),
            raw=data.get("raw"),
        )


@dataclass
class LogFilter:
    """Filter criteria for searching and aggregating log entries."""

    query: str | None = None
    service: str | None = None
    services: list[str] | None = None
    level: LogLevel | None = None
    levels: list[LogLevel] | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    tags: list[str] | None = None
    source: str | None = None
    limit: int = 50
    offset: int = 0
    sort_desc: bool = True


@dataclass
class LogStats:
    """Statistical summary of aggregated log entries."""

    total_logs: int
    by_level: dict[str, int]
    by_service: dict[str, int]
    top_errors: list[dict[str, Any]]
    time_histogram: list[dict[str, Any]]
