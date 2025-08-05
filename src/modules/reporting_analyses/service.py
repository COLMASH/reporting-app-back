"""
Business logic for reporting analysis module - functional approach.

Main Functions:
- create_analysis: Create and execute analysis for a file
- get_analysis_by_id: Retrieve analysis by ID
- get_user_analyses: Get all analyses for a user
- get_file_analyses: Get all analyses for a file
- delete_analysis: Delete analysis and associated results

Error Handling:
- Uses custom exceptions from core.exceptions
- Validates file ownership and existence
- Handles AI service errors gracefully
"""

from datetime import UTC, datetime
from typing import Any, cast
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


def _create_result(
    db: Session,
    analysis_id: UUID,
    result_type: str,
    title: str,
    description: str,
    order_index: int,
    insight_text: str | None = None,
    insight_data: dict | None = None,
) -> None:
    """Helper to create a result record."""
    result = Result(
        analysis_id=analysis_id,
        result_type=result_type,
        title=title,
        description=description,
        insight_text=insight_text,
        insight_data=insight_data,
        order_index=order_index,
    )
    db.add(result)


def _create_results_from_structured_output(
    db: Session,
    analysis_id: UUID,
    structured_output: dict[str, Any],
) -> int:
    """Create result records from structured output.

    Returns:
        Number of results created
    """
    results_created = 0
    order_index = 0

    # Create summary result
    _create_result(
        db=db,
        analysis_id=analysis_id,
        result_type="summary",
        title="Executive Summary",
        description="High-level overview of the Excel analysis",
        insight_text=structured_output.get("summary", "No summary available"),
        order_index=order_index,
    )
    results_created += 1
    order_index += 1

    # Create key metrics result
    if structured_output.get("key_metrics"):
        _create_result(
            db=db,
            analysis_id=analysis_id,
            result_type="metrics",
            title="Key Metrics",
            description="Important KPIs extracted from the data",
            insight_data=structured_output.get("key_metrics"),
            order_index=order_index,
        )
        results_created += 1
        order_index += 1

    # Create visualization results
    if structured_output.get("visualizations"):
        for idx, viz in enumerate(structured_output["visualizations"]):
            _create_result(
                db=db,
                analysis_id=analysis_id,
                result_type="visualization",
                title=viz.get("title", f"Visualization {idx + 1}"),
                description=viz.get("description", ""),
                insight_data=viz,
                order_index=order_index,
            )
            results_created += 1
            order_index += 1

    # Create data quality result
    if structured_output.get("data_quality"):
        _create_result(
            db=db,
            analysis_id=analysis_id,
            result_type="data_quality",
            title="Data Quality Assessment",
            description="Quality metrics and issues found in the data",
            insight_data=structured_output.get("data_quality"),
            order_index=order_index,
        )
        results_created += 1
        order_index += 1

    # Create recommendations result
    if structured_output.get("recommendations"):
        recommendations_text = "\n".join([f"• {rec}" for rec in structured_output["recommendations"]])
        _create_result(
            db=db,
            analysis_id=analysis_id,
            result_type="recommendations",
            title="Business Recommendations",
            description="Actionable insights based on the analysis",
            insight_text=recommendations_text,
            order_index=order_index,
        )
        results_created += 1

    return results_created


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
        started_at=datetime.now(UTC),  # Ensure timezone-aware
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
        result = await analyze_excel_file(str(file.anthropic_file_id), parameters)

        if result.get("success"):
            # Update analysis as completed
            analysis.status = AnalysisStatus.COMPLETED
            analysis.completed_at = datetime.now(UTC)

            # Calculate processing time
            if analysis.started_at and analysis.completed_at:
                # Ensure both timestamps are timezone-aware for comparison
                started = (
                    analysis.started_at.replace(tzinfo=UTC)
                    if analysis.started_at.tzinfo is None
                    else analysis.started_at
                )
                completed = analysis.completed_at
                time_diff = completed - started
                analysis.processing_time_seconds = time_diff.total_seconds()

            # Update token usage
            input_tokens = result.get("input_tokens", 0)
            output_tokens = result.get("output_tokens", 0)
            analysis.input_tokens = input_tokens
            analysis.output_tokens = output_tokens
            analysis.tokens_used = input_tokens + output_tokens

            # Get structured output if available
            structured_output = result.get("structured_output")

            if structured_output:
                results_created = _create_results_from_structured_output(db, cast(UUID, analysis.id), structured_output)
            else:
                # Fallback to simple text result if no structured output
                _create_result(
                    db=db,
                    analysis_id=cast(UUID, analysis.id),
                    result_type="summary",
                    title="Excel File Analysis",
                    description="AI-generated analysis of the Excel file contents",
                    insight_text=result.get("analysis", "No analysis generated"),
                    order_index=0,
                )
                results_created = 1

            logger.info(
                "Analysis completed successfully",
                analysis_id=str(analysis.id),
                has_structured_output=bool(structured_output),
                results_created=results_created,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=analysis.tokens_used,
            )
        else:
            # Update analysis as failed
            analysis.status = AnalysisStatus.FAILED
            error_msg = result.get("error", "Unknown error")
            analysis.error_message = error_msg
            analysis.completed_at = datetime.now(UTC)

            # Calculate processing time even for failed analyses
            if analysis.started_at and analysis.completed_at:
                # Ensure both timestamps are timezone-aware for comparison
                started = (
                    analysis.started_at.replace(tzinfo=UTC)
                    if analysis.started_at.tzinfo is None
                    else analysis.started_at
                )
                completed = analysis.completed_at
                time_diff = completed - started
                analysis.processing_time_seconds = time_diff.total_seconds()

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

        # Calculate processing time even for exceptions
        if analysis.started_at and analysis.completed_at:
            # Ensure both timestamps are timezone-aware for comparison
            started = (
                analysis.started_at.replace(tzinfo=UTC) if analysis.started_at.tzinfo is None else analysis.started_at
            )
            completed = analysis.completed_at
            time_diff = completed - started
            analysis.processing_time_seconds = time_diff.total_seconds()

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


def get_file_analyses(db: Session, file_id: UUID) -> list[Analysis]:
    """
    Get all analyses for a file.

    Args:
        db: Database session
        file_id: UUID of the file

    Returns:
        list[Analysis]: List of analyses ordered by creation date (newest first)
    """
    return db.query(Analysis).filter(Analysis.file_id == file_id).order_by(Analysis.created_at.desc()).all()


def get_user_analyses(db: Session, user_id: UUID) -> list[Analysis]:
    """
    Get all analyses for a user.

    Args:
        db: Database session
        user_id: UUID of the user

    Returns:
        list[Analysis]: List of analyses ordered by creation date (newest first)
    """
    return db.query(Analysis).join(File).filter(File.user_id == user_id).order_by(Analysis.created_at.desc()).all()


def delete_analysis(db: Session, analysis_id: UUID) -> None:
    """
    Delete an analysis and all its associated results.

    Args:
        db: Database session
        analysis_id: UUID of the analysis to delete

    Note:
        Associated results are automatically deleted due to cascade settings.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if analysis:
        db.delete(analysis)
        db.commit()
        logger.info(
            "Analysis deleted successfully",
            analysis_id=str(analysis_id),
            status=analysis.status,
        )
