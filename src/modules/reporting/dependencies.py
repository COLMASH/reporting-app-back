"""
Dependencies for reporting module.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, UploadFile, status

from src.core.config import get_settings
from src.modules.auth.dependencies import CurrentUser, DbSession
from src.modules.reporting.models import Analysis, FileUpload, Result
from src.modules.reporting.service import AnalysisService, FileService, ResultService

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


async def verify_file_ownership(
    file_id: UUID, current_user: CurrentUser, db: DbSession
) -> FileUpload:
    """Verify that the current user owns the file."""
    file = (
        db.query(FileUpload)
        .filter(FileUpload.id == file_id, FileUpload.user_id == current_user.id)
        .first()
    )

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found or access denied"
        )

    return file


FileOwnership = Annotated[FileUpload, Depends(verify_file_ownership)]


async def verify_analysis_ownership(
    analysis_id: UUID, current_user: CurrentUser, db: DbSession
) -> Analysis:
    """Verify that the current user owns the analysis (through file ownership)."""
    analysis = (
        db.query(Analysis)
        .join(FileUpload)
        .filter(Analysis.id == analysis_id, FileUpload.user_id == current_user.id)
        .first()
    )

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found or access denied"
        )

    return analysis


AnalysisOwnership = Annotated[Analysis, Depends(verify_analysis_ownership)]


async def verify_result_ownership(
    result_id: UUID, current_user: CurrentUser, db: DbSession
) -> Result:
    """Verify that the current user owns the result (through analysis/file ownership)."""
    result = (
        db.query(Result)
        .join(Analysis)
        .join(FileUpload)
        .filter(Result.id == result_id, FileUpload.user_id == current_user.id)
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Result not found or access denied"
        )

    return result


ResultOwnership = Annotated[Result, Depends(verify_result_ownership)]


# Service dependencies
def get_file_service(db: DbSession) -> FileService:
    """Get file service instance."""
    return FileService(db)


def get_analysis_service(db: DbSession) -> AnalysisService:
    """Get analysis service instance."""
    return AnalysisService(db)


def get_result_service(db: DbSession) -> ResultService:
    """Get result service instance."""
    return ResultService(db)


FileServiceDep = Annotated[FileService, Depends(get_file_service)]
AnalysisServiceDep = Annotated[AnalysisService, Depends(get_analysis_service)]
ResultServiceDep = Annotated[ResultService, Depends(get_result_service)]
