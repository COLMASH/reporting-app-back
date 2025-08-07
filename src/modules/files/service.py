"""Business logic for files module - functional approach."""

import os
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from src.core.exceptions import NotFoundError, StorageError
from src.core.logging import get_logger
from src.core.storage.anthropic import delete_file_from_anthropic
from src.core.storage.supabase import get_storage_client
from src.modules.files.models import File, FileStatus

logger = get_logger(__name__)

# Pagination constants
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def create_file_metadata(
    db: Session,
    user_id: UUID,
    filename: str,
    original_filename: str,
    supabase_path: str,
    company_name: str,
    **kwargs: Any,
) -> File:
    """Create file metadata record after successful Supabase upload."""
    file_upload = File(
        id=uuid4(),
        user_id=user_id,
        filename=filename,
        original_filename=original_filename,
        supabase_path=supabase_path,
        company_name=company_name,
        file_extension=os.path.splitext(original_filename)[1].lower().replace(".", ""),
        status=FileStatus.UPLOADED,
        **kwargs,
    )

    db.add(file_upload)
    db.commit()
    db.refresh(file_upload)

    logger.info(
        "File metadata created",
        file_id=str(file_upload.id),
        user_id=str(user_id),
        filename=filename,
    )

    return file_upload


def get_user_files(
    db: Session,
    user_id: UUID,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[File], int]:
    """
    Get all files for a user with pagination.

    Args:
        db: Database session
        user_id: User ID
        page: Page number (1-based)
        page_size: Number of results per page

    Returns:
        tuple[list[File], int]: Files and total count
    """
    # Ensure page size is within limits
    page_size = min(page_size, MAX_PAGE_SIZE)
    page = max(1, page)

    # Build query
    query = db.query(File).filter(File.user_id == user_id)

    # Get total count
    total_count = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    files = query.order_by(File.created_at.desc()).offset(offset).limit(page_size).all()

    logger.info(f"Retrieved {len(files)} files for user {user_id} " f"(page {page}, total {total_count})")

    return files, total_count


def get_file_by_id(db: Session, file_id: UUID, user_id: UUID) -> File:
    """Get file by ID, ensuring user ownership."""
    file = db.query(File).filter(File.id == file_id, File.user_id == user_id).first()

    if not file:
        raise NotFoundError(f"File {file_id}")

    return file


async def delete_file(db: Session, file_id: UUID, user_id: UUID) -> None:
    """Delete file and all associated data."""
    file = get_file_by_id(db, file_id, user_id)
    storage = get_storage_client()

    # Delete from Anthropic if file_id exists
    if file.anthropic_file_id:
        try:
            await delete_file_from_anthropic(str(file.anthropic_file_id))
        except StorageError as e:
            logger.error(
                "Failed to delete file from Anthropic",
                file_id=str(file_id),
                anthropic_file_id=file.anthropic_file_id,
                error=str(e),
            )

    # Delete from Supabase storage
    try:
        await storage.delete_file(str(file.supabase_path))
    except StorageError as e:
        logger.error(
            "Failed to delete file from Supabase",
            file_id=str(file_id),
            error=str(e),
        )
        # Continue with database deletion even if storage deletion fails

    # Delete from database (cascade will handle analyses and results)
    db.delete(file)
    db.commit()

    logger.info(
        "File deleted",
        file_id=str(file_id),
        user_id=str(user_id),
    )
