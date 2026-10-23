"""Tests for API dependencies, rate limiting, and global exception handlers."""

import pytest

from log_aggregator.api.deps import (
    RateLimiter,
    get_current_user,
    verify_service_api_key,
)
from log_aggregator.exceptions import (
    AuthenticationError,
    LogAggregatorError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitExceededError,
)
from log_aggregator.main import create_app


def test_rate_limiter_exceeded() -> None:
    limiter = RateLimiter(requests_per_minute=3)
    key = "client-test"
    limiter.check(key)
    limiter.check(key)
    limiter.check(key)

    with pytest.raises(RateLimitExceededError) as exc_info:
        limiter.check(key)
    assert exc_info.value.retry_after > 0


@pytest.mark.asyncio
async def test_verify_service_api_key_valid_and_invalid() -> None:
    # Valid
    service = await verify_service_api_key(x_api_key="secret-auth-key")
    assert service == "auth-service"

    # Missing
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_missing:
        await verify_service_api_key(x_api_key=None)
    assert exc_missing.value.status_code == 401

    # Invalid
    with pytest.raises(HTTPException) as exc_invalid:
        await verify_service_api_key(x_api_key="wrong-key")
    assert exc_invalid.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_token() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        await get_current_user(token=None, bearer_creds=None)

    with pytest.raises(HTTPException):
        await get_current_user(token="invalid.jwt.token", bearer_creds=None)


@pytest.mark.asyncio
async def test_exception_handlers_in_app() -> None:
    import httpx

    app = create_app()

    @app.get("/test-not-found")
    async def raise_not_found() -> None:
        raise NotFoundError("Resource missing")

    @app.get("/test-rate-limit")
    async def raise_rate_limit() -> None:
        raise RateLimitExceededError("Too fast", retry_after=30)

    @app.get("/test-auth-error")
    async def raise_auth_error() -> None:
        raise AuthenticationError("Bad credentials")

    @app.get("/test-forbidden")
    async def raise_forbidden() -> None:
        raise PermissionDeniedError("Action forbidden")

    @app.get("/test-domain-error")
    async def raise_domain_error() -> None:
        raise LogAggregatorError("Domain constraint failed")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        r_nf = await ac.get("/test-not-found")
        assert r_nf.status_code == 404

        r_rl = await ac.get("/test-rate-limit")
        assert r_rl.status_code == 429
        assert r_rl.headers["Retry-After"] == "30"

        r_auth = await ac.get("/test-auth-error")
        assert r_auth.status_code == 401

        r_forbid = await ac.get("/test-forbidden")
        assert r_forbid.status_code == 403

        r_dom = await ac.get("/test-domain-error")
        assert r_dom.status_code == 400
