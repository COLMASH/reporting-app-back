"""
Authentication schemas/models for request/response validation.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class TokenData(BaseModel):
    """Decoded JWT token data from JWT payload."""

    user_id: UUID | str = Field(..., description="User's unique identifier (UUID or string)")
    email: str = Field(..., description="User's email address from token")
    name: str | None = Field(None, description="User's display name")
    image: str | None = Field(None, description="URL to user's profile image")


class UserInfo(BaseModel):
    """User information response."""

    id: UUID = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    name: str | None = Field(None, description="User's full name")
    image: str | None = Field(None, description="URL to user's profile image")
    company_name: str | None = Field(None, description="User's company name")
    role: Literal["user", "admin"] = Field(..., description="User's role in the system")
    is_active: bool = Field(True, description="Whether the user account is active")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = {"from_attributes": True}


# Base class for shared password validation
class PasswordMixin(BaseModel):
    """Mixin for password validation."""

    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description=(
            "Password must contain: 1 lowercase, 1 uppercase, " "1 number, 1 special char (@$!%*?&), min 8 chars"
        ),
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Ensure password meets security requirements:
        - At least one lowercase letter
        - At least one uppercase letter
        - At least one digit
        - At least one special character (@$!%*?&)
        - Minimum 8 characters (already enforced by Field)
        """
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one number")
        if not any(char in "@$!%*?&" for char in v):
            raise ValueError("Password must contain at least one special character (@$!%*?&)")
        return v


class LoginRequest(PasswordMixin):
    """Login request schema."""

    email: EmailStr = Field(..., description="User email address")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
            }
        }
    }


class SignupRequest(PasswordMixin):
    """Signup request schema for creating new users."""

    email: EmailStr = Field(..., description="User email address")
    name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    company_name: str | None = Field(None, max_length=200, description="Optional company name")
    role: Literal["user", "admin"] = Field("user", description="User role (admin/user)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "name": "John Doe",
                "company_name": "Acme Corp",
                "role": "user",
            }
        }
    }


class TokenResponse(BaseModel):
    """JWT token response following OAuth2 standard."""

    access_token: str = Field(..., description="JWT access token")
    token_type: Literal["bearer"] = Field("bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(..., gt=0, description="Token expiration time in seconds")

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
            }
        }
    }
