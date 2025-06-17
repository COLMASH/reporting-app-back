"""
Results endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.auth.service import CurrentUser
from src.database.core import DbSession
from src.results import models

router = APIRouter(prefix="/results", tags=["results"])


@router.get("/analysis/{analysis_id}", response_model=list[models.ResultInfo])
async def get_analysis_results(
    analysis_id: UUID, current_user: CurrentUser, db: DbSession
) -> list[models.ResultInfo]:
    """
    Get all results for a specific analysis.
    """
    # TODO: Implement results retrieval
    return []


@router.get("/{result_id}", response_model=models.ResultDetail)
async def get_result_detail(
    result_id: UUID, current_user: CurrentUser, db: DbSession
) -> models.ResultDetail:
    """
    Get detailed information about a specific result.
    """
    # TODO: Implement result detail retrieval
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
