"""
REST API endpoints for file management.
"""

import io
import os
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status

from src.core.config import settings
from src.core.logging import get_logger
from src.core.storage.anthropic import upload_file_to_anthropic
from src.core.storage.supabase import get_storage_client
from src.modules.auth.dependencies import CurrentUser, DbSession
from src.modules.files import schemas
from src.modules.files import service as file_service
from src.modules.files.dependencies import DbSessionDep, ValidatedFile

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=schemas.FileResponse)
async def upload_file(
    file: ValidatedFile,
    company_name: str,
    current_user: CurrentUser,
    db: DbSessionDep,
    data_classification: schemas.DataClassification | None = None,
) -> schemas.FileResponse:
    """
    Upload a file to storage.

    Only Excel files are supported for analysis.
    """
    try:
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
        unique_filename = f"{uuid4()}{file_extension}"
        supabase_path = f"user_{current_user.id}/{unique_filename}"

        # Read file content
        content = await file.read()

        # First upload to Anthropic
        anthropic_file_id = await upload_file_to_anthropic(
            file_content=content,
            filename=file.filename or "uploaded_file",
        )

        # If Anthropic succeeds, upload to Supabase
        storage = get_storage_client()
        await storage.upload_file(
            file_path=supabase_path,
            file_content=io.BytesIO(content),
            content_type=file.content_type,
        )

        # Create database record with both storage references
        file_metadata = file_service.create_file_metadata(
            db=db,
            user_id=current_user.id,
            filename=unique_filename,
            original_filename=file.filename or "unknown",
            supabase_path=supabase_path,
            company_name=company_name,
            data_classification=data_classification,
            file_size=file.size or len(content),
            mime_type=file.content_type,
            supabase_bucket=settings.supabase_bucket_name,
            anthropic_file_id=anthropic_file_id,
        )

        logger.info(
            "File uploaded successfully",
            user_id=str(current_user.id),
            file_id=str(file_metadata.id),
            filename=file.filename,
        )

        return file_metadata

    except Exception as e:
        logger.error(
            "File upload failed", user_id=str(current_user.id), filename=file.filename, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}",
        ) from e


@router.get("/", response_model=schemas.FileListResponse)
async def list_files(current_user: CurrentUser, db: DbSession) -> schemas.FileListResponse:
    """List all files for the current user."""
    files = file_service.get_user_files(db, current_user.id)

    return schemas.FileListResponse(
        files=[schemas.FileResponse.model_validate(f) for f in files],
        total=len(files),
    )


@router.get("/{file_id}", response_model=schemas.FileResponse)
async def get_file(file_id: str, current_user: CurrentUser, db: DbSession) -> schemas.FileResponse:
    """Get details for a specific file."""
    try:
        file_uuid = UUID(file_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file ID format",
        ) from None

    file = file_service.get_file_by_id(db, file_uuid, current_user.id)
    return schemas.FileResponse.model_validate(file)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(file_id: str, current_user: CurrentUser, db: DbSessionDep) -> None:
    """Delete a file and all associated data."""
    try:
        file_uuid = UUID(file_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file ID format",
        ) from None

    await file_service.delete_file(db, file_uuid, current_user.id)
