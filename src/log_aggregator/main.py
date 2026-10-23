"""Application entrypoint and FastAPI factory.

Initializes application dependencies, lifespan events, and exception handlers.
No business logic or endpoint route handlers reside in this file.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from log_aggregator.api.deps import (
    get_evaluator,
    get_ingester,
    get_notifier,
    get_storage,
    get_streamer,
)
from log_aggregator.api.router import api_router
from log_aggregator.api.stream import router as stream_root_router
from log_aggregator.config import settings
from log_aggregator.exceptions import (
    AuthenticationError,
    LogAggregatorError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitExceededError,
)
from log_aggregator.transport.tcp_server import TcpLogServer

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("log_aggregator")

tcp_server: TcpLogServer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle events."""
    global tcp_server
    logger.info("Starting Log Aggregator service in %s mode", settings.ENVIRONMENT)

    # Initialize storage backend and verify connectivity
    storage = get_storage()
    is_healthy = await storage.ping()
    logger.info(
        "Storage backend initialized. Health status: %s",
        "healthy" if is_healthy else "unreachable",
    )

    # Start optional TCP log receiver
    if settings.TCP_SERVER_ENABLED:
        ingester = get_ingester(
            storage=storage,
            streamer=get_streamer(),
            evaluator=get_evaluator(),
            notifier=get_notifier(),
        )
        tcp_server = TcpLogServer(
            ingester=ingester,
            host=settings.TCP_SERVER_HOST,
            port=settings.TCP_SERVER_PORT,
        )
        try:
            await tcp_server.start()
        except Exception as exc:
            logger.warning(
                "Failed to start TCP Log Server on %s:%d: %s",
                settings.TCP_SERVER_HOST,
                settings.TCP_SERVER_PORT,
                exc,
            )

    yield

    # Teardown TCP server
    if tcp_server:
        await tcp_server.stop()

    # Close HTTP notifier client
    notifier = get_notifier()
    await notifier.close()

    # Close storage connections
    await storage.close()
    logger.info("Log Aggregator service shut down successfully")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="Log Aggregator Service",
        description=(
            "Centralized log ingestion, parsing, Elasticsearch indexing, "
            "full-text search, real-time WebSocket tailing, and alerting service."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # Enable CORS for dashboards and web clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global domain exception handlers
    @app.exception_handler(RateLimitExceededError)
    async def rate_limit_handler(
        request: Request,
        exc: RateLimitExceededError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": exc.message, "retry_after": exc.retry_after},
            headers={"Retry-After": str(exc.retry_after)},
        )

    @app.exception_handler(NotFoundError)
    async def not_found_handler(
        request: Request,
        exc: NotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": exc.message},
        )

    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(
        request: Request,
        exc: AuthenticationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": exc.message},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(PermissionDeniedError)
    async def forbidden_handler(
        request: Request,
        exc: PermissionDeniedError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": exc.message},
        )

    @app.exception_handler(LogAggregatorError)
    async def general_error_handler(
        request: Request,
        exc: LogAggregatorError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": exc.message},
        )

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check() -> dict[str, Any]:
        storage = get_storage()
        storage_healthy = await storage.ping()
        return {
            "status": "healthy" if storage_healthy else "degraded",
            "environment": settings.ENVIRONMENT,
            "storage_healthy": storage_healthy,
        }

    # Mount API and WebSocket routers
    app.include_router(api_router)
    app.include_router(stream_root_router)

    return app


app = create_app()
