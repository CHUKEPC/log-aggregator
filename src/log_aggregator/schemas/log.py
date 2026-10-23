"""Pydantic schemas for log ingestion, search queries, and responses.

Provides serialization and request validation for HTTP and WebSocket endpoints.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from log_aggregator.models.log_entry import LogEntry, LogFormat, LogLevel


class LogCreateRequest(BaseModel):
    """Schema for submitting a single structured log entry."""

    message: str = Field(..., min_length=1, description="Log message text")
    service: str = Field(..., min_length=1, max_length=128, description="Originating service name")
    level: LogLevel = Field(default=LogLevel.INFO, description="Log severity level")
    source: str = Field(default="api", max_length=256, description="Source host or subsystem")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp in UTC when log occurred",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary JSON metadata fields"
    )
    tags: list[str] = Field(default_factory=list, description="Categorization tags")

    def to_domain(self) -> LogEntry:
        """Convert schema to core domain LogEntry model."""
        return LogEntry(
            message=self.message,
            service=self.service,
            level=self.level,
            source=self.source,
            timestamp=self.timestamp,
            metadata=self.metadata,
            tags=self.tags,
            raw=None,
        )


class RawLogCreateRequest(BaseModel):
    """Schema for submitting a single unparsed raw log line."""

    raw: str = Field(..., min_length=1, description="Raw unparsed log line")
    format: LogFormat | None = Field(
        default=None,
        description="Optional explicit log format (JSON, SYSLOG, NGINX, APACHE, REGEX)",
    )
    service: str | None = Field(default=None, description="Optional service name override")
    source: str = Field(default="raw-ingest", description="Source identifier")


class BatchLogCreateRequest(BaseModel):
    """Schema for bulk ingestion of structured log records."""

    logs: list[LogCreateRequest] = Field(
        ..., min_length=1, max_length=10000, description="List of structured log entries"
    )


class BatchRawLogCreateRequest(BaseModel):
    """Schema for bulk ingestion of unparsed raw log lines."""

    lines: list[str] = Field(
        ..., min_length=1, max_length=10000, description="List of raw log lines"
    )
    format: LogFormat | None = Field(default=None, description="Format of raw lines")
    service: str | None = Field(default=None, description="Service name fallback")
    source: str = Field(default="batch-raw", description="Source identifier")


class LogResponse(BaseModel):
    """Schema representing a stored log entry returned to clients."""

    id: str
    timestamp: datetime
    level: LogLevel
    service: str
    message: str
    source: str
    metadata: dict[str, Any]
    tags: list[str]
    raw: str | None = None

    @classmethod
    def from_domain(cls, entry: LogEntry) -> "LogResponse":
        """Build schema from domain LogEntry entity."""
        return cls(
            id=entry.id,
            timestamp=entry.timestamp,
            level=entry.level,
            service=entry.service,
            message=entry.message,
            source=entry.source,
            metadata=entry.metadata,
            tags=entry.tags,
            raw=entry.raw,
        )


class LogSearchResponse(BaseModel):
    """Schema for paginated log search results."""

    total: int = Field(..., description="Total matching logs count")
    limit: int = Field(..., description="Page limit")
    offset: int = Field(..., description="Page offset")
    logs: list[LogResponse] = Field(..., description="List of matching logs")


class LogStatsResponse(BaseModel):
    """Schema for aggregated metrics and summary charts."""

    total_logs: int
    by_level: dict[str, int]
    by_service: dict[str, int]
    top_errors: list[dict[str, Any]]
    time_histogram: list[dict[str, Any]]


class IngestResponse(BaseModel):
    """Response returned upon successful log ingestion."""

    ingested: int = Field(..., description="Count of successfully ingested logs")
    errors: list[str] = Field(default_factory=list, description="Parsing or ingestion errors")
