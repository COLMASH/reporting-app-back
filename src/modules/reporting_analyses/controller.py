"""
REST API endpoints for reporting analysis.

Main Functions:
- create_analysis: Create new analysis for a file
- get_analysis: Get specific analysis details
- get_user_analyses: Get all analyses for current user
- get_file_analyses: Get all analyses for a specific file
- delete_analysis: Delete analysis and associated results

Dependencies:
- CurrentUser: Authenticated user from JWT token
- DbSession: Database session for queries
"""

from uuid import UUID

from fastapi import APIRouter, Request

from src.core.decorators import log_endpoint
from src.core.exceptions import NotFoundError, ValidationError
from src.core.logging import get_logger
from src.modules.auth.dependencies import CurrentUser, DbSession
from src.modules.files.service import get_file_by_id
from src.modules.reporting_analyses import schemas
from src.modules.reporting_analyses import service as reporting_service

logger = get_logger(__name__)

# Create router with detailed metadata
router = APIRouter(
    prefix="/reporting_analysis",
    tags=["reporting_analysis"],
    responses={
        404: {"description": "Analysis or file not found"},
        403: {"description": "Access forbidden - user doesn't own the file"},
        500: {"description": "Internal server error"},
    },
)


@router.post("/", response_model=schemas.AnalysisResponse)
@log_endpoint
async def create_analysis(
    request: schemas.AnalysisCreateRequest,
    req: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> schemas.AnalysisResponse:
    """
    Create a new analysis for a file.

    The user must own the file to create an analysis.
    Analysis runs immediately using the configured AI agent.
    """
    # Verify user owns the file
    try:
        get_file_by_id(db, request.file_id, current_user.id)
    except NotFoundError:
        raise NotFoundError(f"File {request.file_id} not found") from None

    # Create and run analysis
    try:
        analysis = await reporting_service.create_analysis(
            db=db,
            file_id=request.file_id,
            parameters=request.parameters,
        )
        logger.info(
            "Analysis created successfully",
            analysis_id=str(analysis.id),
            file_id=str(request.file_id),
            user_id=str(current_user.id),
        )
        return analysis
    except ValueError as e:
        raise ValidationError(str(e)) from e
    except Exception as e:
        logger.error(
            "Failed to create analysis",
            error=str(e),
            file_id=str(request.file_id),
            user_id=str(current_user.id),
        )
        raise


@router.get("/{reporting_analysis_id}", response_model=schemas.AnalysisResponse)
@log_endpoint
async def get_analysis(
    reporting_analysis_id: str,
    req: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> schemas.AnalysisResponse:
    """
    Get analysis details by ID.

    The user must own the file associated with the analysis.
    """
    try:
        analysis_uuid = UUID(reporting_analysis_id)
    except ValueError:
        raise ValidationError("Invalid analysis ID format") from None

    analysis = reporting_service.get_analysis_by_id(db, analysis_uuid)
    if not analysis:
        raise NotFoundError(f"Analysis {reporting_analysis_id} not found")

    # Verify user owns the file
    try:
        get_file_by_id(db, analysis.file_id, current_user.id)
    except NotFoundError:
        raise NotFoundError(f"Analysis {reporting_analysis_id} not found") from None

    return analysis


@router.get("/", response_model=schemas.AnalysisListResponse)
@log_endpoint
async def get_user_analyses(
    req: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> schemas.AnalysisListResponse:
    """
    Get all analyses for the current user.

    Returns analyses ordered by creation date (newest first).
    """
    analyses = reporting_service.get_user_analyses(db, current_user.id)

    logger.info(
        "Retrieved user analyses",
        user_id=str(current_user.id),
        count=len(analyses),
    )

    return schemas.AnalysisListResponse(
        analyses=analyses,
        total=len(analyses),
    )


@router.get("/file/{file_id}", response_model=schemas.AnalysisListResponse)
@log_endpoint
async def get_file_analyses(
    file_id: str,
    req: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> schemas.AnalysisListResponse:
    """
    Get all analyses for a specific file.

    The user must own the file to view its analyses.
    Returns analyses ordered by creation date (newest first).
    """
    try:
        file_uuid = UUID(file_id)
    except ValueError:
        raise ValidationError("Invalid file ID format") from None

    # Verify user owns the file
    try:
        get_file_by_id(db, file_uuid, current_user.id)
    except NotFoundError:
        raise NotFoundError(f"File {file_id} not found") from None

    analyses = reporting_service.get_file_analyses(db, file_uuid)

    logger.info(
        "Retrieved file analyses",
        file_id=file_id,
        user_id=str(current_user.id),
        count=len(analyses),
    )

    return schemas.AnalysisListResponse(
        analyses=analyses,
        total=len(analyses),
    )


@router.delete("/{reporting_analysis_id}", status_code=204)
@log_endpoint
async def delete_analysis(
    reporting_analysis_id: str,
    req: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """
    Delete an analysis and all its associated results.

    The user must own the file associated with the analysis.
    This permanently removes the analysis and all its results.
    """
    try:
        analysis_uuid = UUID(reporting_analysis_id)
    except ValueError:
        raise ValidationError("Invalid analysis ID format") from None

    # Get the analysis
    analysis = reporting_service.get_analysis_by_id(db, analysis_uuid)
    if not analysis:
        raise NotFoundError(f"Analysis {reporting_analysis_id} not found")

    # Verify user owns the file
    try:
        get_file_by_id(db, analysis.file_id, current_user.id)
    except NotFoundError:
        raise NotFoundError(f"Analysis {reporting_analysis_id} not found") from None

    # Delete the analysis
    reporting_service.delete_analysis(db, analysis_uuid)

    logger.info(
        "Analysis deleted successfully",
        analysis_id=reporting_analysis_id,
        user_id=str(current_user.id),
    )
