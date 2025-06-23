"""
File upload and management endpoints.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from src.auth.dependencies import CurrentUser, DbSession
from src.files import schemas

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=schemas.FileUploadResponse)
async def upload_file(
    file: Annotated[UploadFile, File(...)],
    current_user: CurrentUser,
    db: DbSession,
    company_name: str | None = None,
    department: str | None = None,
    classification: str | None = None,
) -> schemas.FileUploadResponse:
    """
    Upload an Excel file for processing.

    - **file**: Excel file (.xlsx or .xls)
    - **company_name**: Company name for the file
    - **department**: Department (optional)
    - **classification**: Data classification (portfolio, operations, etc.)
    """
    # TODO: Implement file upload logic
    return schemas.FileUploadResponse(
        id="temp-id",
        filename=file.filename or "unknown.xlsx",
        status="uploaded",
        message="File upload endpoint - implementation pending",
    )


@router.get("/", response_model=list[schemas.FileInfo])
async def list_files(current_user: CurrentUser, db: DbSession) -> list[schemas.FileInfo]:
    """
    List all files uploaded by the current user.
    """
    # TODO: Implement file listing logic
    return []


@router.get("/{file_id}", response_model=schemas.FileInfo)
async def get_file_info(
    file_id: UUID, current_user: CurrentUser, db: DbSession
) -> schemas.FileInfo:
    """
    Get information about a specific file.
    """
    # TODO: Implement file info retrieval
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
