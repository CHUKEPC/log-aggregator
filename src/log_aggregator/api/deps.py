"""API dependencies for security, rate limiting, and service injection.

Handles JWT verification, API key authentication, and client rate limiting.
"""

import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import jwt
from fastapi import Depends, Header, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer

from log_aggregator.alerts.evaluator import AlertEvaluator
from log_aggregator.alerts.notifier import AlertNotifier
from log_aggregator.config import Settings, settings
from log_aggregator.exceptions import RateLimitExceededError
from log_aggregator.schemas.auth import TokenPayload
from log_aggregator.services.alerter import AlertService
from log_aggregator.services.ingester import LogIngester
from log_aggregator.services.retention import RetentionService
from log_aggregator.services.searcher import LogSearcher
from log_aggregator.services.streamer import LogStreamer
from log_aggregator.storage.base import LogStorage
from log_aggregator.storage.elasticsearch import ElasticsearchLogStorage
from log_aggregator.storage.memory import InMemoryLogStorage

# Singleton application instances managed during lifecycle
_storage: LogStorage | None = None
_streamer: LogStreamer = LogStreamer()
_evaluator: AlertEvaluator = AlertEvaluator()
_notifier: AlertNotifier = AlertNotifier()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)
http_bearer = HTTPBearer(auto_error=False)


def get_settings() -> Settings:
    """Return application configuration settings."""
    return settings


def get_storage() -> LogStorage:
    """Return initialized storage backend."""
    global _storage
    if _storage is None:
        if settings.USE_MEMORY_STORAGE or settings.ENVIRONMENT == "testing":
            _storage = InMemoryLogStorage()
        else:
            _storage = ElasticsearchLogStorage(settings)
    return _storage


def set_storage(storage: LogStorage) -> None:
    """Explicitly override storage backend (used in tests or initialization)."""
    global _storage
    _storage = storage


def get_streamer() -> LogStreamer:
    """Return real-time log streamer manager."""
    return _streamer


def get_evaluator() -> AlertEvaluator:
    """Return alert evaluator instance."""
    return _evaluator


def get_notifier() -> AlertNotifier:
    """Return alert notifier instance."""
    return _notifier


def get_ingester(
    storage: Annotated[LogStorage, Depends(get_storage)],
    streamer: Annotated[LogStreamer, Depends(get_streamer)],
    evaluator: Annotated[AlertEvaluator, Depends(get_evaluator)],
    notifier: Annotated[AlertNotifier, Depends(get_notifier)],
) -> LogIngester:
    """Dependency provider for LogIngester."""
    return LogIngester(
        storage=storage,
        streamer=streamer,
        evaluator=evaluator,
        notifier=notifier,
    )


def get_searcher(
    storage: Annotated[LogStorage, Depends(get_storage)],
) -> LogSearcher:
    """Dependency provider for LogSearcher."""
    return LogSearcher(storage=storage)


def get_alerter(
    evaluator: Annotated[AlertEvaluator, Depends(get_evaluator)],
    notifier: Annotated[AlertNotifier, Depends(get_notifier)],
) -> AlertService:
    """Dependency provider for AlertService."""
    return AlertService(evaluator=evaluator, notifier=notifier)


def get_retention(
    storage: Annotated[LogStorage, Depends(get_storage)],
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> RetentionService:
    """Dependency provider for RetentionService."""
    return RetentionService(storage=storage, settings=app_settings)


def create_access_token(
    subject: str,
    role: str = "admin",
    expires_delta: timedelta | None = None,
) -> str:
    """Generate encoded JWT bearer token."""
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": int(expire.timestamp()),
        "role": role,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
    bearer_creds: Annotated[HTTPAuthorizationCredentials | None, Security(http_bearer)] = None,
) -> TokenPayload:
    """Validate JWT token and return authenticated user token payload."""
    raw_token = token or (bearer_creds.credentials if bearer_creds else None)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            raw_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return TokenPayload(**payload)
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def verify_service_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> str:
    """Verify service API key passed in headers."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )
    for service_name, key in settings.API_KEYS.items():
        if key == x_api_key:
            return service_name

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )


async def get_current_client(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
    bearer_creds: Annotated[HTTPAuthorizationCredentials | None, Security(http_bearer)] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> str:
    """Authenticate request using either JWT token or service API key."""
    # Check API key first if provided
    if x_api_key:
        for service_name, key in settings.API_KEYS.items():
            if key == x_api_key:
                return f"service:{service_name}"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Check JWT token
    raw_token = token or (bearer_creds.credentials if bearer_creds else None)
    if raw_token:
        try:
            payload = jwt.decode(
                raw_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
            )
            return f"user:{payload.get('sub', 'unknown')}"
        except jwt.PyJWTError:
            pass

    # Allow unauthenticated access in development/testing mode if explicitly configured
    if settings.DEBUG or settings.ENVIRONMENT == "development":
        client_host = request.client.host if request.client else "unknown"
        return f"dev:{client_host}"

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required via Bearer JWT or X-API-Key",
        headers={"WWW-Authenticate": "Bearer"},
    )


class RateLimiter:
    """In-memory sliding window rate limiter per client key."""

    def __init__(self, requests_per_minute: int = 600) -> None:
        """Initialize requests capacity limit and tracking container."""
        self.requests_per_minute = requests_per_minute
        self._history: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> None:
        """Record and verify client request rate against limit."""
        now = time.time()
        window_start = now - 60.0
        timestamps = self._history[key]

        # Evict timestamps older than 60 seconds
        valid = [ts for ts in timestamps if ts > window_start]
        if len(valid) >= self.requests_per_minute:
            retry_after = int(60.0 - (now - valid[0]))
            raise RateLimitExceededError(
                f"Rate limit exceeded: max {self.requests_per_minute} requests/min",
                retry_after=max(1, retry_after),
            )

        valid.append(now)
        self._history[key] = valid


_global_limiter = RateLimiter(requests_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE)


async def check_rate_limit(
    request: Request,
    client_id: Annotated[str, Depends(get_current_client)],
) -> None:
    """Dependency that enforces rate limits per client identity or IP."""
    try:
        _global_limiter.check(client_id)
    except RateLimitExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=exc.message,
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
