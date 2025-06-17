"""
Authentication service for JWT validation and user management.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session

from src.auth import models
from src.config import settings
from src.database.core import get_db
from src.entities.user import User
from src.exceptions import AuthenticationError

# Security scheme
security = HTTPBearer()
logger = logging.getLogger(__name__)


def decode_token(token: str) -> models.TokenData:
    """
    Decode and validate JWT token from NextAuth.

    NextAuth tokens typically include:
    - sub: Subject (user email)
    - name: User's full name
    - email: User's email
    - picture: User's profile picture URL
    - iat: Issued at timestamp
    - exp: Expiration timestamp
    """
    try:
        # Decode token without verification for NextAuth compatibility
        # In production, you should verify with the same secret NextAuth uses
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_signature": True},
        )

        # Extract user information from NextAuth token
        email: str = payload.get("email") or payload.get("sub")
        if not email:
            raise AuthenticationError("Invalid token: missing email")

        # NextAuth uses different field names, so we map them
        return models.TokenData(
            user_id=payload.get("id", 0),  # Will be set from database
            email=email,
            name=payload.get("name"),
            image=payload.get("picture") or payload.get("image"),
        )

    except PyJWTError as e:
        logger.warning(f"Token validation failed: {str(e)}")
        raise AuthenticationError("Invalid or expired token") from e


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """
    Get current user from JWT token.
    Creates user if they don't exist (for NextAuth integration).
    """
    token = credentials.credentials
    token_data = decode_token(token)

    # Look up user by email
    user = db.query(User).filter(User.email == token_data.email).first()

    # If user doesn't exist, create them (NextAuth handles registration)
    if not user:
        user = User(
            email=token_data.email,
            name=token_data.name,
            image=token_data.image,
            emailVerified=datetime.now(UTC),
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created new user from NextAuth token: {user.email}")

    # Update token_data with actual user ID
    if user.id is not None:
        token_data.user_id = int(user.id)  # Convert to int for mypy

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
        )

    return user


async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


async def get_admin_user(current_user: Annotated[User, Depends(get_current_active_user)]) -> User:
    """Get current user and verify they are an admin."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user


# Type aliases for dependency injection
CurrentUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(get_admin_user)]


# Development/Testing only - Create JWT token
def create_access_token(user: User, expires_delta: timedelta | None = None) -> str:
    """
    Create JWT token for development/testing.
    In production, NextAuth handles token creation.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expiration_minutes)

    to_encode = {
        "sub": user.email,
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "image": user.image,
        "exp": expire,
        "iat": datetime.now(UTC),
    }

    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt
