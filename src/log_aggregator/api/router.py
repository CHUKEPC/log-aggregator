"""API router aggregation module.

Combines all sub-routers under the common `/api/v1` prefix.
"""

from fastapi import APIRouter

from log_aggregator.api.alerts import router as alerts_router
from log_aggregator.api.auth import router as auth_router
from log_aggregator.api.ingest import router as ingest_router
from log_aggregator.api.retention import router as retention_router
from log_aggregator.api.search import router as search_router
from log_aggregator.api.stats import router as stats_router
from log_aggregator.api.stream import router as stream_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(ingest_router)
api_router.include_router(search_router)
api_router.include_router(stats_router)
api_router.include_router(alerts_router)
api_router.include_router(retention_router)
api_router.include_router(stream_router)
