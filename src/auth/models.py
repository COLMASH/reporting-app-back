"""
Authentication schemas/models for request/response validation.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class TokenData(BaseModel):
    """Decoded JWT token data."""

    user_id: int
    email: str
    name: str | None = None
    image: str | None = None

    def get_user_id(self) -> int:
        """Get user ID as integer."""
        return self.user_id


class UserInfo(BaseModel):
    """User information response."""

    id: int
    email: str | None
    name: str | None
    image: str | None
    company_name: str | None
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr
    password: str = Field(..., min_length=8)


class SignupRequest(BaseModel):
    """Signup request schema for creating new users."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str
    company_name: str | None = None
    role: str = Field(default="user", pattern="^(user|admin)$")


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
