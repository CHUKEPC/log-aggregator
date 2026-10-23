"""Authentication endpoints for issuing JWT tokens.

Provides token creation and user identity introspection.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from log_aggregator.api.deps import create_access_token, get_current_user
from log_aggregator.config import settings
from log_aggregator.schemas.auth import LoginRequest, TokenPayload, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponse:
    """Issue a JWT bearer access token using OAuth2 password flow."""
    # Compare with configured administrator credentials
    if (
        form_data.username != settings.ADMIN_USERNAME
        or form_data.password != settings.ADMIN_PASSWORD
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=form_data.username, role="admin")
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.post("/login", response_model=TokenResponse)
async def login_json(credentials: LoginRequest) -> TokenResponse:
    """Issue a JWT bearer access token using JSON payload."""
    if (
        credentials.username != settings.ADMIN_USERNAME
        or credentials.password != settings.ADMIN_PASSWORD
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    token = create_access_token(subject=credentials.username, role="admin")
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.get("/me", response_model=TokenPayload)
async def read_current_user(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
) -> TokenPayload:
    """Return identity and claims of the authenticated user."""
    return current_user
