"""Statistics and metrics API endpoints.

Aggregates logs by severity level, originating service, error frequency, and time histogram.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from log_aggregator.api.deps import get_searcher
from log_aggregator.models.log_entry import LogFilter, LogLevel
from log_aggregator.schemas.log import LogStatsResponse
from log_aggregator.services.searcher import LogSearcher

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("", response_model=LogStatsResponse)
async def get_log_statistics(
    searcher: Annotated[LogSearcher, Depends(get_searcher)],
    service: Annotated[str | None, Query(description="Filter statistics by service")] = None,
    level: Annotated[LogLevel | None, Query(description="Filter statistics by level")] = None,
    start_time: Annotated[datetime | None, Query(description="Start time window")] = None,
    end_time: Annotated[datetime | None, Query(description="End time window")] = None,
) -> LogStatsResponse:
    """Retrieve log counts by level, service, top errors, and time histogram."""
    filter_query = LogFilter(
        service=service,
        level=level,
        start_time=start_time,
        end_time=end_time,
    )

    stats = await searcher.get_stats(filter_query)
    return LogStatsResponse(
        total_logs=stats.total_logs,
        by_level=stats.by_level,
        by_service=stats.by_service,
        top_errors=stats.top_errors,
        time_histogram=stats.time_histogram,
    )
