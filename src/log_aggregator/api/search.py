"""Log search and retrieval endpoints.

Provides full-text search, filtering across attributes, and pagination.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from log_aggregator.api.deps import get_searcher
from log_aggregator.exceptions import NotFoundError
from log_aggregator.models.log_entry import LogFilter, LogLevel
from log_aggregator.schemas.log import LogResponse, LogSearchResponse
from log_aggregator.services.searcher import LogSearcher

router = APIRouter(prefix="", tags=["Search & Retrieval"])


@router.get("/search", response_model=LogSearchResponse)
async def search_logs(
    searcher: Annotated[LogSearcher, Depends(get_searcher)],
    q: Annotated[str | None, Query(description="Full-text query search")] = None,
    service: Annotated[str | None, Query(description="Service name filter")] = None,
    level: Annotated[LogLevel | None, Query(description="Log severity level filter")] = None,
    source: Annotated[str | None, Query(description="Source identifier filter")] = None,
    start_time: Annotated[datetime | None, Query(description="Start timestamp in UTC")] = None,
    end_time: Annotated[datetime | None, Query(description="End timestamp in UTC")] = None,
    tags: Annotated[list[str] | None, Query(description="Tag filters")] = None,
    limit: Annotated[int, Query(ge=1, le=1000, description="Result page limit")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
    sort_desc: Annotated[bool, Query(description="Sort descending by timestamp")] = True,
) -> LogSearchResponse:
    """Search and filter stored logs."""
    filter_query = LogFilter(
        query=q,
        service=service,
        level=level,
        source=source,
        start_time=start_time,
        end_time=end_time,
        tags=tags,
        limit=limit,
        offset=offset,
        sort_desc=sort_desc,
    )

    entries, total = await searcher.search(filter_query)
    return LogSearchResponse(
        total=total,
        limit=limit,
        offset=offset,
        logs=[LogResponse.from_domain(e) for e in entries],
    )


@router.get("/logs/{log_id}", response_model=LogResponse)
async def get_log_by_id(
    log_id: str,
    searcher: Annotated[LogSearcher, Depends(get_searcher)],
) -> LogResponse:
    """Retrieve an individual log record by its UUID."""
    try:
        entry = await searcher.get_by_id(log_id)
        return LogResponse.from_domain(entry)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
