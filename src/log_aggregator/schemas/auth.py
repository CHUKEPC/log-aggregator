"""Pydantic schemas for authentication and JWT tokens.

Handles user credentials and token responses.
"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Schema for user authentication request."""

    username: str = Field(..., description="User account name")
    password: str = Field(..., description="Plain-text password")


class TokenResponse(BaseModel):
    """Schema for returning bearer access tokens."""

    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class TokenPayload(BaseModel):
    """Decoded JWT payload data."""

    sub: str
    exp: int
    role: str = "admin"
