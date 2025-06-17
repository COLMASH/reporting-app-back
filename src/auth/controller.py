"""
Authentication endpoints.
"""

from datetime import UTC, datetime

from fastapi import APIRouter

from src.auth import models, service
from src.auth.service import CurrentUser, OptionalUser
from src.database.core import DbSession
from src.exceptions import AuthenticationError

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/me", response_model=models.UserInfo)
async def get_current_user_info(current_user: CurrentUser) -> models.UserInfo:
    """
    Get current user information.
    Requires valid JWT token.
    """
    return models.UserInfo.model_validate(current_user)


@router.post("/verify", response_model=models.UserInfo)
async def verify_token(current_user: CurrentUser) -> models.UserInfo:
    """
    Verify JWT token and return user information.
    Used to check if token is still valid.
    """
    return models.UserInfo.model_validate(current_user)


@router.post("/signup", response_model=models.UserInfo)
async def signup(
    request: models.SignupRequest,
    db: DbSession,
    current_user: OptionalUser
) -> models.UserInfo:
    """
    Create a new user account.
    If users exist, requires admin authentication.
    First user created is automatically admin.
    """
    from src.entities.user import User
    from src.exceptions import ConflictError

    # Check if this is the first user
    user_count = db.query(User).count()

    # If users exist, require admin authentication
    if user_count > 0:
        if not current_user:
            raise AuthenticationError("Authentication required")
        if current_user.role != "admin":
            raise AuthenticationError("Admin access required")

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise ConflictError("User with this email already exists")

    # First user is automatically admin, regardless of requested role
    # After that, use the requested role (admins can create other admins)
    role = "admin" if user_count == 0 else request.role

    # Create new user
    user = User(
        email=request.email,
        password_hash=service.hash_password(request.password),
        name=request.name,
        company_name=request.company_name,
        role=role,
        emailVerified=datetime.now(UTC),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return models.UserInfo.model_validate(user)


@router.post("/login", response_model=models.TokenResponse)
async def login(request: models.LoginRequest, db: DbSession) -> models.TokenResponse:
    """
    Login with email and password.
    Only works for users created via signup endpoint.
    """
    from src.entities.user import User
    from src.exceptions import AuthenticationError

    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise AuthenticationError("Invalid email or password")

    # Check if user has a password (was created via signup)
    if not user.password_hash:
        raise AuthenticationError("Invalid email or password")

    # Verify password
    # Type assertion needed because SQLAlchemy columns are typed as Column[str]
    password_hash: str = user.password_hash  # type: ignore[assignment]
    if not service.verify_password(request.password, password_hash):
        raise AuthenticationError("Invalid email or password")

    # Check if user is active
    if not user.is_active:
        raise AuthenticationError("Account is disabled")

    # Create token
    access_token = service.create_access_token(user)

    return models.TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=service.settings.jwt_expiration_minutes * 60,
    )
