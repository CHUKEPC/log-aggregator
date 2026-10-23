"""Log ingestion API endpoints.

Accepts structured logs and raw unparsed log lines individually and in batches.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from log_aggregator.api.deps import check_rate_limit, get_ingester
from log_aggregator.schemas.log import (
    BatchLogCreateRequest,
    BatchRawLogCreateRequest,
    IngestResponse,
    LogCreateRequest,
    LogResponse,
    RawLogCreateRequest,
)
from log_aggregator.services.ingester import LogIngester

router = APIRouter(
    prefix="/ingest",
    tags=["Ingestion"],
    dependencies=[Depends(check_rate_limit)],
)


@router.post("", response_model=LogResponse, status_code=status.HTTP_201_CREATED)
async def ingest_single_log(
    request: LogCreateRequest,
    ingester: Annotated[LogIngester, Depends(get_ingester)],
) -> LogResponse:
    """Ingest a single structured log entry."""
    entry = await ingester.ingest_single(request)
    return LogResponse.from_domain(entry)


@router.post("/batch", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_batch_logs(
    request: BatchLogCreateRequest,
    ingester: Annotated[LogIngester, Depends(get_ingester)],
) -> IngestResponse:
    """Bulk ingest multiple structured log entries."""
    return await ingester.ingest_batch(request.logs)


@router.post("/raw", response_model=LogResponse, status_code=status.HTTP_201_CREATED)
async def ingest_raw_log(
    request: RawLogCreateRequest,
    ingester: Annotated[LogIngester, Depends(get_ingester)],
) -> LogResponse:
    """Ingest a single unparsed raw log line with automatic or specified parsing."""
    entry = await ingester.ingest_raw_single(request)
    return LogResponse.from_domain(entry)


@router.post("/raw/batch", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_raw_batch_logs(
    request: BatchRawLogCreateRequest,
    ingester: Annotated[LogIngester, Depends(get_ingester)],
) -> IngestResponse:
    """Bulk ingest multiple unparsed raw log lines."""
    return await ingester.ingest_raw_batch(
        lines=request.lines,
        explicit_format=request.format,
        service=request.service,
        source=request.source,
    )
