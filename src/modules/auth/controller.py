"""
Authentication endpoints.
"""

from fastapi import APIRouter, Request

from src.core.decorators import log_endpoint
from src.modules.auth import schemas
from src.modules.auth.dependencies import CurrentUser, DbSession, OptionalUser
from src.modules.auth.service import login_user, signup_user

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/me", response_model=schemas.UserInfo)
@log_endpoint
async def get_current_user_info(
    request: Request,
    current_user: CurrentUser,
) -> schemas.UserInfo:
    """
    Get current user information.
    Requires valid JWT token.
    """
    return schemas.UserInfo.model_validate(current_user)


@router.post("/verify", response_model=schemas.UserInfo)
@log_endpoint
async def verify_token(
    request: Request,
    current_user: CurrentUser,
) -> schemas.UserInfo:
    """
    Verify JWT token and return user information.
    Used to check if token is still valid.
    """
    return schemas.UserInfo.model_validate(current_user)


@router.post("/signup", response_model=schemas.UserInfo)
@log_endpoint
async def signup(
    signup_request: schemas.SignupRequest,
    request: Request,
    current_user: OptionalUser,
    db: DbSession,
) -> schemas.UserInfo:
    """
    Create a new user account.
    If users exist, requires admin authentication.
    First user created is automatically admin.
    """
    user = await signup_user(signup_request, current_user, db)
    return schemas.UserInfo.model_validate(user)


@router.post("/login", response_model=schemas.TokenResponse)
@log_endpoint
async def login(
    login_request: schemas.LoginRequest,
    request: Request,
    db: DbSession,
) -> schemas.TokenResponse:
    """
    Login with email and password.
    Only works for users created via signup endpoint.
    """
    return await login_user(login_request.email, login_request.password, db)
