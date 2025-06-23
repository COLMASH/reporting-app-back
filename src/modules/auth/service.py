"""
Authentication service with JWT validation and user management.

Main Functions:
- signup_user: Create new user accounts
- login_user: Authenticate with email/password

Dependency Hierarchy:
security/security_optional → get_current_user → get_current_active_user → get_admin_user
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database.core import get_db
from src.core.exceptions import AuthenticationError
from src.modules.auth import schemas
from src.modules.auth.models import User

logger = logging.getLogger(__name__)

# =============================================================================
# Constants and Security Schemes
# =============================================================================

# Security scheme for required authentication
security = HTTPBearer()

# Security scheme for optional authentication
security_optional = HTTPBearer(auto_error=False)


# =============================================================================
# Utility Functions - Password Hashing
# =============================================================================


def hash_password(password: str) -> str:
    """Hash a password for storing."""
    # Generate salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a hashed password against a plain text password."""
    # Check if the password matches the hash
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


# =============================================================================
# Utility Functions - Token Management
# =============================================================================


def decode_token(token: str) -> schemas.TokenData:
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
        # Handle UUID from token - it might be a string
        user_id = payload.get("id", "")

        return schemas.TokenData(
            user_id=user_id,  # UUID will be validated when used
            email=email,
            name=payload.get("name"),
            image=payload.get("picture") or payload.get("image"),
        )

    except PyJWTError as e:
        logger.warning(f"Token validation failed: {str(e)}")
        raise AuthenticationError("Invalid or expired token") from e


# =============================================================================
# Dependency Functions - Authentication Checks
# =============================================================================


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """
    Get current user from JWT token.
    User must exist in database (created via signup endpoint).

    Dependencies:
    - security: Extracts JWT from Authorization header (required)
    - get_db: Provides database session
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


async def get_current_user_optional(
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_optional)],
) -> User | None:
    """
    Get current user from JWT token if provided.
    Returns None if no token is provided or token is invalid.
    Used for endpoints that have conditional authentication.

    Dependencies:
    - security_optional: Extracts JWT from Authorization header (optional)
    - get_db: Provides database session
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


async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    Get current active user.

    Dependencies:
    - get_current_user: Provides authenticated user
    """
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


async def get_admin_user(current_user: Annotated[User, Depends(get_current_active_user)]) -> User:
    """
    Get current user and verify they are an admin.

    Dependencies:
    - get_current_active_user: Provides active authenticated user
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user


# =============================================================================
# Business Logic Functions
# =============================================================================


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
        "id": str(user.id),  # Convert UUID to string for JSON serialization
        "email": user.email,
        "name": user.name,
        "image": user.image,
        "exp": expire,
        "iat": datetime.now(UTC),
    }

    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt


async def signup_user(
    signup_data: schemas.SignupRequest,
    current_user: User | None,
    db: Session,
) -> User:
    """
    Create a new user account.

    Business rules:
    - First user is automatically admin
    - After that, only admins can create users
    - Email must be unique
    """
    from src.core.exceptions import ConflictError

    # Check if this is the first user
    user_count = db.query(User).count()

    # If users exist, require admin authentication
    if user_count > 0:
        if not current_user:
            raise AuthenticationError("Authentication required")
        if current_user.role != "admin":
            raise AuthenticationError("Admin access required")

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == signup_data.email).first()
    if existing_user:
        raise ConflictError("User with this email already exists")

    # First user is automatically admin, regardless of requested role
    role = "admin" if user_count == 0 else signup_data.role

    # Create new user
    user = User(
        email=signup_data.email,
        password_hash=hash_password(signup_data.password),
        name=signup_data.name,
        company_name=signup_data.company_name,
        role=role,
        emailVerified=datetime.now(UTC),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"Created new user: {user.email} with role: {role}")
    return user


async def login_user(email: str, password: str, db: Session) -> schemas.TokenResponse:
    """
    Login user with email/password and return access token.

    Only works for users created via signup endpoint (with passwords).
    """
    # Find user by email
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise AuthenticationError("Invalid email or password")

    # Check if user has a password (was created via signup)
    if not user.password_hash:
        raise AuthenticationError("Invalid email or password")

    # Verify password
    # Type assertion needed because SQLAlchemy columns are typed as Column[str]
    password_hash: str = user.password_hash  # type: ignore[assignment]
    if not verify_password(password, password_hash):
        raise AuthenticationError("Invalid email or password")

    # Check if user is active
    if not user.is_active:
        raise AuthenticationError("Account is disabled")

    # Create token
    access_token = create_access_token(user)

    return schemas.TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_expiration_minutes * 60,
    )
