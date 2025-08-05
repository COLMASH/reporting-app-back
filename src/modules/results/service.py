"""
Result management service with functional programming approach.

Main Functions:
- get_result_by_id: Retrieve a single result with ownership validation
- get_analysis_results: Get all results for an analysis
- get_user_results: Get all results for a user with pagination
- delete_result: Delete a result with ownership validation
- get_file_results: Get all results for a specific file

Error Handling:
- Uses custom exceptions from core.exceptions
- Validates user ownership through file/analysis chain
- Ensures proper access control
"""

import logging
from uuid import UUID

from sqlalchemy import desc, func
from sqlalchemy.orm import Session, joinedload

from src.core.exceptions import NotFoundError, PermissionError
from src.modules.auth.models import User
from src.modules.files.models import File
from src.modules.reporting_analyses.models import Analysis
from src.modules.results.models import Result

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


# =============================================================================
# Utility Functions - Access Control
# =============================================================================


def validate_result_access(db: Session, result: Result, user: User) -> None:
    """
    Validate that a user has access to a result.

    Access is granted if:
    - User owns the file associated with the analysis
    - User is an admin

    Raises:
        PermissionError: If user doesn't have access
    """
    # Admin users have access to all results
    if user.role == "admin":
        return

    # Load analysis with file relationship
    analysis = db.query(Analysis).options(joinedload(Analysis.file)).filter(Analysis.id == result.analysis_id).first()

    if not analysis:
        logger.warning(f"Result {result.id} has invalid analysis_id {result.analysis_id}")
        raise PermissionError("Access denied")

    # Check if user owns the file
    if analysis.file.user_id != user.id:
        raise PermissionError("Access denied")


def validate_analysis_access(db: Session, analysis: Analysis, user: User) -> None:
    """
    Validate that a user has access to an analysis.

    Access is granted if:
    - User owns the file associated with the analysis
    - User is an admin

    Raises:
        PermissionError: If user doesn't have access
    """
    # Admin users have access to all analyses
    if user.role == "admin":
        return

    # Load file relationship if not already loaded
    if not analysis.file:
        db.refresh(analysis, ["file"])

    # Check if user owns the file
    if analysis.file.user_id != user.id:
        raise PermissionError("Access denied")


# =============================================================================
# Business Logic Functions - Retrieval
# =============================================================================


def get_result_by_id(db: Session, result_id: UUID, user: User) -> Result:
    """
    Get a single result by ID with access validation.

    Args:
        db: Database session
        result_id: UUID of the result
        user: Current user making the request

    Returns:
        Result: The requested result

    Raises:
        NotFoundError: If result doesn't exist
        PermissionError: If user doesn't have access
    """
    result = db.query(Result).filter(Result.id == result_id).first()

    if not result:
        raise NotFoundError(f"Result {result_id} not found")

    # Validate access
    validate_result_access(db, result, user)

    return result


def get_analysis_results(db: Session, analysis_id: UUID, user: User) -> list[Result]:
    """
    Get all results for an analysis with access validation.

    Args:
        db: Database session
        analysis_id: UUID of the analysis
        user: Current user making the request

    Returns:
        list[Result]: Results ordered by order_index

    Raises:
        NotFoundError: If analysis doesn't exist
        PermissionError: If user doesn't have access
    """
    # First check if analysis exists
    analysis = db.query(Analysis).options(joinedload(Analysis.file)).filter(Analysis.id == analysis_id).first()

    if not analysis:
        raise NotFoundError(f"Analysis {analysis_id} not found")

    # Validate access
    validate_analysis_access(db, analysis, user)

    # Get all results for this analysis
    results = db.query(Result).filter(Result.analysis_id == analysis_id).order_by(Result.order_index).all()

    logger.info(f"Retrieved {len(results)} results for analysis {analysis_id}")

    return results


def get_user_results(
    db: Session,
    user: User,
    result_type: str | None = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[Result], int]:
    """
    Get all results for a user with optional filtering and pagination.

    Args:
        db: Database session
        user: Current user
        result_type: Optional filter by result type
        page: Page number (1-based)
        page_size: Number of results per page

    Returns:
        tuple[list[Result], int]: Results and total count
    """
    # Ensure page size is within limits
    page_size = min(page_size, MAX_PAGE_SIZE)
    page = max(1, page)

    # Build base query with joins
    query = db.query(Result).join(Analysis).join(File).filter(File.user_id == user.id)

    # Apply result type filter if provided
    if result_type:
        query = query.filter(Result.result_type == result_type)

    # Get total count
    total_count = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    results = query.order_by(desc(Result.created_at)).offset(offset).limit(page_size).all()

    logger.info(f"Retrieved {len(results)} results for user {user.id} " f"(page {page}, total {total_count})")

    return results, total_count


def get_file_results(db: Session, file_id: UUID, user: User) -> list[Result]:
    """
    Get all results for a specific file with access validation.

    Args:
        db: Database session
        file_id: UUID of the file
        user: Current user making the request

    Returns:
        list[Result]: All results for the file, ordered by analysis date and order_index

    Raises:
        NotFoundError: If file doesn't exist
        PermissionError: If user doesn't have access
    """
    # Check if file exists and user has access
    file = db.query(File).filter(File.id == file_id).first()

    if not file:
        raise NotFoundError(f"File {file_id} not found")

    # Check access (admin or file owner)
    if user.role != "admin" and file.user_id != user.id:
        raise PermissionError("Access denied")

    # Get all results for analyses of this file
    results = db.query(Result).join(Analysis).filter(Analysis.file_id == file_id).order_by(desc(Analysis.created_at), Result.order_index).all()

    logger.info(f"Retrieved {len(results)} results for file {file_id}")

    return results


# =============================================================================
# Business Logic Functions - Deletion
# =============================================================================


def delete_result(db: Session, result_id: UUID, user: User) -> None:
    """
    Delete a result with access validation.

    Only the file owner or admin can delete results.

    Args:
        db: Database session
        result_id: UUID of the result to delete
        user: Current user making the request

    Raises:
        NotFoundError: If result doesn't exist
        PermissionError: If user doesn't have permission to delete
    """
    result = db.query(Result).filter(Result.id == result_id).first()

    if not result:
        raise NotFoundError(f"Result {result_id} not found")

    # Validate access
    validate_result_access(db, result, user)

    # Delete the result
    db.delete(result)
    db.commit()

    logger.info(f"Deleted result {result_id} by user {user.id}")


# =============================================================================
# Business Logic Functions - Aggregation
# =============================================================================


def get_result_statistics(db: Session, user: User) -> dict:
    """
    Get statistics about results for a user.

    Args:
        db: Database session
        user: Current user

    Returns:
        dict: Statistics including counts by type
    """
    # Build query based on user role
    if user.role == "admin":
        base_query = db.query(Result.result_type, func.count(Result.id))
    else:
        base_query = db.query(Result.result_type, func.count(Result.id)).join(Analysis).join(File).filter(File.user_id == user.id)

    # Get counts by type
    type_counts = base_query.group_by(Result.result_type).all()

    # Calculate total
    total = sum(count for _, count in type_counts)

    # Convert to dict manually to avoid type issues
    by_type_dict = {}
    for result_type, count in type_counts:
        by_type_dict[result_type] = count

    return {
        "total": total,
        "by_type": by_type_dict,
    }
