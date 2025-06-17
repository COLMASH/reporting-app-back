"""
Authentication endpoints.
"""

from fastapi import APIRouter

from src.auth import models, service
from src.auth.service import CurrentUser
from src.database.core import DbSession

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/me", response_model=models.UserInfo)
async def get_current_user_info(current_user: CurrentUser) -> models.UserInfo:
    """
    Get current user information.
    Requires valid JWT token from NextAuth.
    """
    return models.UserInfo.from_orm(current_user)


@router.post("/verify", response_model=models.UserInfo)
async def verify_token(current_user: CurrentUser) -> models.UserInfo:
    """
    Verify JWT token and return user information.
    Used to check if token is still valid.
    """
    return models.UserInfo.from_orm(current_user)


# Development/Testing endpoints - Remove in production
if True:  # Change to False in production

    @router.post("/dev/login", response_model=models.TokenResponse)
    async def dev_login(request: models.LoginRequest, db: DbSession) -> models.TokenResponse:
        """
        Development login endpoint.
        In production, NextAuth handles authentication.
        """
        # For development, accept any email/password and create user if needed
        from src.entities.user import User

        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            user = User(email=request.email, name="Dev User", emailVerified=None, is_active=True)
            db.add(user)
            db.commit()
            db.refresh(user)

        # Create token
        access_token = service.create_access_token(user)

        return models.TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=service.settings.jwt_expiration_minutes * 60,
        )
