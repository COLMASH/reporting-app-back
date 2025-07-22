"""
REST API endpoints for results.

Endpoints:
- GET /results/{result_id}: Get a single result by ID
- GET /results/analysis/{analysis_id}: Get all results for an analysis
- GET /results/file/{file_id}: Get all results for a file
- GET /results/user/me: Get current user's results with pagination
- GET /results/statistics: Get result statistics for current user
- DELETE /results/{result_id}: Delete a result
"""

from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from src.core.decorators import log_endpoint
from src.core.exceptions import ValidationError
from src.modules.auth.dependencies import CurrentUser, DbSession
from src.modules.results import schemas
from src.modules.results.service import (
    delete_result,
    get_analysis_results,
    get_file_results,
    get_result_by_id,
    get_result_statistics,
    get_user_results,
)

# Create router
router = APIRouter(prefix="/results", tags=["results"])


@router.get("/{result_id}", response_model=schemas.ResultResponse)
@log_endpoint
async def get_result(
    request: Request,
    result_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> schemas.ResultResponse:
    """
    Get result details by ID.

    Access Control:
    - User must own the file associated with the result
    - Admin users can access all results
    """
    result = get_result_by_id(db, result_id, current_user)
    return schemas.ResultResponse.model_validate(result)


@router.get("/analysis/{analysis_id}", response_model=schemas.ResultListResponse)
@log_endpoint
async def get_results_by_analysis(
    request: Request,
    analysis_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> schemas.ResultListResponse:
    """
    Get all results for an analysis.

    Results are returned in order_index order.

    Access Control:
    - User must own the file associated with the analysis
    - Admin users can access all results
    """
    results = get_analysis_results(db, analysis_id, current_user)
    return schemas.ResultListResponse(
        results=[schemas.ResultResponse.model_validate(r) for r in results],
        total=len(results),
    )


@router.get("/file/{file_id}", response_model=schemas.ResultListResponse)
@log_endpoint
async def get_results_by_file(
    request: Request,
    file_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> schemas.ResultListResponse:
    """
    Get all results for a file across all analyses.

    Results are ordered by analysis creation date and order_index.

    Access Control:
    - User must own the file
    - Admin users can access all files
    """
    results = get_file_results(db, file_id, current_user)
    return schemas.ResultListResponse(
        results=[schemas.ResultResponse.model_validate(r) for r in results],
        total=len(results),
    )


@router.get("/user/me", response_model=schemas.ResultListResponse)
@log_endpoint
async def get_my_results(
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
    result_type: str | None = Query(
        None,
        description="Filter by result type: visualization, metrics, summary, data_quality, recommendations",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
) -> schemas.ResultListResponse:
    """
    Get all results for the current user with pagination.

    Optional Filters:
    - result_type: Filter by specific result type

    Pagination:
    - page: Page number (default: 1)
    - page_size: Results per page (default: 20, max: 100)
    """
    # Validate result_type if provided
    valid_types = {"visualization", "metrics", "summary", "data_quality", "recommendations"}
    if result_type and result_type not in valid_types:
        raise ValidationError(f"Invalid result_type. Must be one of: {', '.join(valid_types)}")

    results, total = get_user_results(db, current_user, result_type, page, page_size)

    return schemas.ResultListResponse(
        results=[schemas.ResultResponse.model_validate(r) for r in results],
        total=total,
    )


@router.get("/statistics", response_model=dict)
@log_endpoint
async def get_my_statistics(
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Get result statistics for the current user.

    Returns:
    - total: Total number of results
    - by_type: Count of results by type
    """
    return get_result_statistics(db, current_user)


@router.delete("/{result_id}", status_code=status.HTTP_204_NO_CONTENT)
@log_endpoint
async def delete_result_endpoint(
    request: Request,
    result_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """
    Delete a result.

    Access Control:
    - User must own the file associated with the result
    - Admin users can delete any result
    """
    delete_result(db, result_id, current_user)
