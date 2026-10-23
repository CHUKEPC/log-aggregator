"""Pytest fixtures and test environment setup.

Provides mocked and in-memory dependencies for unit and integration testing.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

from log_aggregator.alerts.evaluator import AlertEvaluator
from log_aggregator.alerts.notifier import AlertNotifier
from log_aggregator.api.deps import (
    create_access_token,
    get_evaluator,
    get_notifier,
    get_storage,
    get_streamer,
    set_storage,
)
from log_aggregator.main import create_app
from log_aggregator.models.log_entry import LogEntry, LogLevel
from log_aggregator.services.alerter import AlertService
from log_aggregator.services.ingester import LogIngester
from log_aggregator.services.retention import RetentionService
from log_aggregator.services.searcher import LogSearcher
from log_aggregator.services.streamer import LogStreamer
from log_aggregator.storage.memory import InMemoryLogStorage


@pytest.fixture
def storage() -> InMemoryLogStorage:
    """Return a fresh in-memory storage backend."""
    return InMemoryLogStorage()


@pytest.fixture
def streamer() -> LogStreamer:
    """Return a real-time log streamer."""
    return LogStreamer()


@pytest.fixture
def evaluator() -> AlertEvaluator:
    """Return a fresh alert evaluator."""
    return AlertEvaluator(max_window_minutes=60, cooldown_seconds=0)


@pytest.fixture
def notifier() -> AlertNotifier:
    """Return an alert notifier with mocked HTTP dispatcher."""
    notifier_inst = AlertNotifier(history_limit=100)
    # Mock the internal client so no external requests are made
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = httpx.Response(status_code=200)
    mock_client.post.return_value = mock_resp
    notifier_inst._http_client = mock_client
    return notifier_inst


@pytest.fixture
def ingester(
    storage: InMemoryLogStorage,
    streamer: LogStreamer,
    evaluator: AlertEvaluator,
    notifier: AlertNotifier,
) -> LogIngester:
    """Return configured LogIngester."""
    return LogIngester(
        storage=storage,
        streamer=streamer,
        evaluator=evaluator,
        notifier=notifier,
    )


@pytest.fixture
def searcher(storage: InMemoryLogStorage) -> LogSearcher:
    """Return LogSearcher with storage."""
    return LogSearcher(storage=storage)


@pytest.fixture
def alerter(evaluator: AlertEvaluator, notifier: AlertNotifier) -> AlertService:
    """Return AlertService."""
    return AlertService(evaluator=evaluator, notifier=notifier)


@pytest.fixture
def retention(storage: InMemoryLogStorage) -> RetentionService:
    """Return RetentionService."""
    from log_aggregator.config import settings

    return RetentionService(storage=storage, settings=settings)


@pytest.fixture
def app(
    storage: InMemoryLogStorage,
    streamer: LogStreamer,
    evaluator: AlertEvaluator,
    notifier: AlertNotifier,
) -> FastAPI:
    """Create FastAPI application wired with in-memory test dependencies."""
    set_storage(storage)
    test_app = create_app()

    test_app.dependency_overrides[get_storage] = lambda: storage
    test_app.dependency_overrides[get_streamer] = lambda: streamer
    test_app.dependency_overrides[get_evaluator] = lambda: evaluator
    test_app.dependency_overrides[get_notifier] = lambda: notifier

    return test_app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """Return async HTTP test client using ASGITransport."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Generate authorization header with valid JWT token."""
    token = create_access_token(subject="admin", role="admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def service_api_key_headers() -> dict[str, str]:
    """Generate header with valid service API key."""
    return {"X-API-Key": "secret-auth-key"}


@pytest.fixture
def sample_log_entries() -> list[LogEntry]:
    """Generate a diverse set of sample LogEntry records for testing."""
    now = datetime.now(UTC)
    return [
        LogEntry(
            id="11111111-1111-1111-1111-111111111111",
            message="User logged in successfully",
            service="auth-service",
            level=LogLevel.INFO,
            source="host-01",
            timestamp=now - timedelta(minutes=15),
            metadata={"user_id": 101, "ip": "192.168.1.10"},
            tags=["auth", "login"],
        ),
        LogEntry(
            id="22222222-2222-2222-2222-222222222222",
            message="Database connection pool saturated",
            service="payment-service",
            level=LogLevel.WARNING,
            source="host-02",
            timestamp=now - timedelta(minutes=10),
            metadata={"active_connections": 100},
            tags=["db", "warning"],
        ),
        LogEntry(
            id="33333333-3333-3333-3333-333333333333",
            message="Failed to process credit card transaction",
            service="payment-service",
            level=LogLevel.ERROR,
            source="host-02",
            timestamp=now - timedelta(minutes=5),
            metadata={"transaction_id": "tx-999", "error": "timeout"},
            tags=["payment", "error"],
        ),
        LogEntry(
            id="44444444-4444-4444-4444-444444444444",
            message="Fatal kernel out-of-memory killed worker",
            service="worker-service",
            level=LogLevel.CRITICAL,
            source="worker-node-3",
            timestamp=now - timedelta(minutes=1),
            metadata={"signal": 9},
            tags=["infra", "critical"],
        ),
        LogEntry(
            id="55555555-5555-5555-5555-555555555555",
            message="Cache hit for user profile",
            service="auth-service",
            level=LogLevel.DEBUG,
            source="host-01",
            timestamp=now,
            metadata={"cache_key": "user:101"},
            tags=["cache"],
        ),
    ]
