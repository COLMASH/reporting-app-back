"""
Dependencies for files module.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, UploadFile, status

from src.core.config import get_settings
from src.modules.auth.dependencies import CurrentUser, DbSession
from src.modules.files.models import File

settings = get_settings()


def validate_file_upload(file: UploadFile) -> UploadFile:
    """Validate uploaded file."""
    # Check file extension
    if file.filename:
        extension = file.filename.lower().split(".")[-1]
        if f".{extension}" not in settings.allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid file type. Allowed extensions: "
                    f"{', '.join(settings.allowed_extensions)}"
                ),
            )

    # Check file size (if content_length is available)
    if file.size and file.size > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB",
        )

    return file


ValidatedFile = Annotated[UploadFile, Depends(validate_file_upload)]


async def verify_file_ownership(file_id: UUID, current_user: CurrentUser, db: DbSession) -> File:
    """Verify that the current user owns the file."""
    file = db.query(File).filter(File.id == file_id, File.user_id == current_user.id).first()

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found or access denied"
        )

    return file


FileOwnership = Annotated[File, Depends(verify_file_ownership)]


# Functional service dependencies
def get_db_session(db: DbSession) -> DbSession:
    """Pass through database session for functional services."""
    return db


DbSessionDep = Annotated[DbSession, Depends(get_db_session)]
