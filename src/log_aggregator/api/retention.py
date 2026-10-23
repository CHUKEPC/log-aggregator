"""Retention policy API endpoints.

Triggers manual and scheduled pruning of old log entries based on TTL.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from log_aggregator.api.deps import get_retention
from log_aggregator.services.retention import RetentionService

router = APIRouter(prefix="/retention", tags=["Retention"])


@router.post("/cleanup")
async def trigger_retention_cleanup(
    retention: Annotated[RetentionService, Depends(get_retention)],
    days: Annotated[
        int | None,
        Query(ge=1, description="Override retention days; defaults to configured RETENTION_DAYS"),
    ] = None,
) -> dict[str, Any]:
    """Execute retention policy cleanup to delete expired logs."""
    purged_count = await retention.cleanup_old_logs(retention_days=days)
    return {
        "status": "success",
        "purged_count": purged_count,
        "retention_days": days or retention.default_retention_days,
    }
