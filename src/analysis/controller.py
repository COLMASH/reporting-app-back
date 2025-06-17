"""
Analysis endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.analysis import models
from src.auth.service import CurrentUser
from src.database.core import DbSession

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/", response_model=models.AnalysisResponse)
async def create_analysis(
    request: models.AnalysisRequest, current_user: CurrentUser, db: DbSession
) -> models.AnalysisResponse:
    """
    Create a new analysis job for a file.
    """
    # TODO: Implement analysis creation
    return models.AnalysisResponse(
        id="temp-id",
        file_id=request.file_id,
        status="pending",
        agent_type=request.agent_type,
        message="Analysis endpoint - implementation pending",
    )


@router.get("/{analysis_id}", response_model=models.AnalysisInfo)
async def get_analysis_status(
    analysis_id: UUID, current_user: CurrentUser, db: DbSession
) -> models.AnalysisInfo:
    """
    Get analysis status and progress.
    """
    # TODO: Implement analysis status retrieval
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")


@router.get("/file/{file_id}", response_model=list[models.AnalysisInfo])
async def get_file_analyses(
    file_id: UUID, current_user: CurrentUser, db: DbSession
) -> list[models.AnalysisInfo]:
    """
    Get all analyses for a specific file.
    """
    # TODO: Implement file analyses retrieval
    return []
