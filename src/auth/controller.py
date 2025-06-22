"""
Authentication endpoints.
"""

from fastapi import APIRouter

from src.auth import models
from src.auth.service import CurrentUser, OptionalUser, login_user, signup_user
from src.database.core import DbSession

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
    current_user: OptionalUser,
    db: DbSession,
) -> models.UserInfo:
    """
    Create a new user account.
    If users exist, requires admin authentication.
    First user created is automatically admin.
    """
    user = await signup_user(request, current_user, db)
    return models.UserInfo.model_validate(user)


@router.post("/login", response_model=models.TokenResponse)
async def login(
    request: models.LoginRequest,
    db: DbSession,
) -> models.TokenResponse:
    """
    Login with email and password.
    Only works for users created via signup endpoint.
    """
    return await login_user(request.email, request.password, db)
