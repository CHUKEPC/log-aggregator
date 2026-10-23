"""Pydantic schemas for alert rules configuration and triggered events.

Supports pattern-based thresholds, condition evaluation, and notifications.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from log_aggregator.models.log_entry import LogLevel


class AlertCondition(StrEnum):
    """Conditions that trigger an alert rule."""

    ERROR_COUNT = "ERROR_COUNT"
    KEYWORD_MATCH = "KEYWORD_MATCH"
    LOG_RATE = "LOG_RATE"


class AlertRuleCreate(BaseModel):
    """Schema for registering a new alert rule."""

    name: str = Field(..., min_length=2, max_length=128, description="Descriptive rule name")
    condition: AlertCondition = Field(..., description="Condition type to check")
    service: str | None = Field(default=None, description="Optional service scope filter")
    level: LogLevel | None = Field(default=None, description="Target log level filter")
    pattern: str | None = Field(default=None, description="Keyword or regex pattern for matching")
    threshold: int = Field(default=5, ge=1, description="Trigger threshold count")
    window_minutes: int = Field(default=1, ge=1, le=1440, description="Time window in minutes")
    webhook_url: str | None = Field(default=None, description="Webhook endpoint for notifications")
    enabled: bool = Field(default=True, description="Whether this rule is actively evaluated")


class AlertRuleResponse(AlertRuleCreate):
    """Schema returned for configured alert rules."""

    id: str
    created_at: datetime


class AlertEventResponse(BaseModel):
    """Schema for recording a triggered alert occurrence."""

    id: str
    rule_id: str
    rule_name: str
    triggered_at: datetime
    message: str
    count: int
