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
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src.auth import models
from src.config import settings
from src.database.core import get_db
from src.entities.user import User
from src.exceptions import AuthenticationError

# Security scheme
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password for storing."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a hashed password against a plain text password."""
    return pwd_context.verify(plain_password, hashed_password)


def decode_token(token: str) -> models.TokenData:
    """
    Decode and validate JWT token.

    Expected token fields:
    - sub: Subject (user email)
    - name: User's full name
    - email: User's email
    - picture: User's profile picture URL
    - iat: Issued at timestamp
    - exp: Expiration timestamp
    """
    try:
        # Decode token with verification using shared secret
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

        # Map token fields to our token data structure
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
    User must exist in database (created via signup endpoint).
    """
    token = credentials.credentials
    token_data = decode_token(token)

    # Look up user by email
    user = db.query(User).filter(User.email == token_data.email).first()

    # User must exist
    if not user:
        logger.warning(f"Authentication attempt for non-existent user: {token_data.email}")
        raise AuthenticationError("User not found")

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


async def get_current_user_optional(
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_optional)],
) -> User | None:
    """
    Get current user from JWT token if provided.
    Returns None if no token is provided or token is invalid.
    Used for endpoints that have conditional authentication.
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        token_data = decode_token(token)

        # Look up user by email
        user = db.query(User).filter(User.email == token_data.email).first()

        # Only return user if they exist and are active
        if user and user.is_active:
            return user

        # Log authentication attempts for non-existent users
        if not user:
            logger.warning(f"Optional auth attempt for non-existent user: {token_data.email}")

    except Exception as e:
        # Log the error but don't raise - this is optional auth
        logger.debug(f"Optional auth failed: {str(e)}")
        pass

    return None


# Optional user dependency
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]


def create_access_token(user: User, expires_delta: timedelta | None = None) -> str:
    """
    Create JWT token for user authentication.
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
