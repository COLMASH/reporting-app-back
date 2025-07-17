"""
Business logic for reporting analysis module - functional approach.

Main Functions:
- create_analysis: Create and execute analysis for a file
- get_analysis_by_id: Retrieve analysis by ID
- get_user_analyses: Get all analyses for a user
- get_file_analyses: Get all analyses for a file
- update_analysis_status: Update analysis status (TODO)
- cancel_analysis: Cancel analysis execution (TODO)

Error Handling:
- Uses custom exceptions from core.exceptions
- Validates file ownership and existence
- Handles AI service errors gracefully
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from src.core.exceptions import (
    AIServiceError,
    NotFoundError,
    ValidationError,
)
from src.core.logging import get_logger
from src.modules.files.models import File
from src.modules.reporting_analyses.agent import analyze_excel_file
from src.modules.reporting_analyses.models import Analysis, AnalysisStatus
from src.modules.results.models import Result

logger = get_logger(__name__)


async def create_analysis(db: Session, file_id: UUID, parameters: dict | None = None) -> Analysis:
    """
    Create a new analysis job and run the agent.

    Args:
        db: Database session
        file_id: UUID of the file to analyze
        parameters: Optional parameters for the analysis agent

    Returns:
        Analysis: The created analysis with results

    Raises:
        NotFoundError: If file doesn't exist
        ValidationError: If file has no Anthropic file ID
        AIServiceError: If AI service fails
    """
    # Get the file to ensure it exists and get anthropic_file_id
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        raise NotFoundError(f"File {file_id} not found")

    if not file.anthropic_file_id:
        raise ValidationError(f"File {file_id} has no Anthropic file ID")

    # Create analysis record
    analysis = Analysis(
        file_id=file_id,
        parameters=parameters,
        status=AnalysisStatus.IN_PROGRESS,
        started_at=datetime.now(UTC),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    try:
        # Run the agent
        logger.info(
            "Starting analysis execution",
            analysis_id=str(analysis.id),
            file_id=str(file_id),
            anthropic_file_id=file.anthropic_file_id,
        )
        result = await analyze_excel_file(str(file.anthropic_file_id))

        if result.get("success"):
            # Update analysis as completed
            analysis.status = AnalysisStatus.COMPLETED
            analysis.completed_at = datetime.now(UTC)

            # Create result record
            analysis_result = Result(
                analysis_id=analysis.id,
                result_type="summary",
                title="Excel File Analysis",
                description="AI-generated analysis of the Excel file contents",
                insight_text=result.get("analysis", "No analysis generated"),
                order_index=0,
                is_primary=True,
            )
            db.add(analysis_result)

            logger.info(
                "Analysis completed successfully",
                analysis_id=str(analysis.id),
                result_length=len(result.get("analysis", "")),
            )
        else:
            # Update analysis as failed
            analysis.status = AnalysisStatus.FAILED
            error_msg = result.get("error", "Unknown error")
            analysis.error_message = error_msg
            analysis.completed_at = datetime.now(UTC)

            logger.error(
                "Analysis failed - agent returned error",
                analysis_id=str(analysis.id),
                error=error_msg,
            )

    except Exception as e:
        # Update analysis as failed
        analysis.status = AnalysisStatus.FAILED
        analysis.error_message = str(e)
        analysis.completed_at = datetime.now(UTC)

        logger.error(
            "Analysis failed - exception occurred",
            analysis_id=str(analysis.id),
            file_id=str(file_id),
            error=str(e),
        )

        # Re-raise as AIServiceError for better error handling
        raise AIServiceError(f"Analysis execution failed: {str(e)}") from e

    db.commit()
    db.refresh(analysis)

    return analysis


def get_analysis_by_id(db: Session, analysis_id: UUID) -> Analysis | None:
    """
    Get analysis by ID.

    Args:
        db: Database session
        analysis_id: UUID of the analysis to retrieve

    Returns:
        Analysis | None: The analysis if found, None otherwise
    """
    return db.query(Analysis).filter(Analysis.id == analysis_id).first()


# TODO: Implement update_analysis_status function
def update_analysis_status(db: Session, analysis_id: UUID, status: str, **kwargs: Any) -> Analysis:
    """Update analysis status and related fields."""
    # TODO: Implement status update logic
    raise NotImplementedError("update_analysis_status not yet implemented")


def get_file_analyses(db: Session, file_id: UUID) -> list[Analysis]:
    """
    Get all analyses for a file.

    Args:
        db: Database session
        file_id: UUID of the file

    Returns:
        list[Analysis]: List of analyses ordered by creation date (newest first)
    """
    return (
        db.query(Analysis)
        .filter(Analysis.file_id == file_id)
        .order_by(Analysis.created_at.desc())
        .all()
    )


def get_user_analyses(db: Session, user_id: UUID) -> list[Analysis]:
    """
    Get all analyses for a user.

    Args:
        db: Database session
        user_id: UUID of the user

    Returns:
        list[Analysis]: List of analyses ordered by creation date (newest first)
    """
    return (
        db.query(Analysis)
        .join(File)
        .filter(File.user_id == user_id)
        .order_by(Analysis.created_at.desc())
        .all()
    )


# TODO: Implement cancel_analysis function
def cancel_analysis(db: Session, analysis_id: UUID) -> None:
    """Cancel a pending or in-progress analysis."""
    # TODO: Implement analysis cancellation logic
    raise NotImplementedError("cancel_analysis not yet implemented")
