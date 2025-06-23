"""
Authentication dependencies for dependency injection.

This module contains reusable dependencies that can be injected into
FastAPI endpoints. These are separated from the service layer to avoid
circular imports and improve code organization.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from src.auth.models import User
from src.auth.service import get_admin_user, get_current_active_user, get_current_user_optional
from src.database.core import get_db

# Database session dependency
DbSession = Annotated[Session, Depends(get_db)]

# User authentication dependencies
CurrentUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(get_admin_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
