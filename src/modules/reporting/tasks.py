"""
Background tasks for processing analyses.
"""

import time
from typing import Any
from uuid import UUID

from fastapi import BackgroundTasks

from src.core.database.core import SessionLocal
from src.core.logging import get_logger
from src.modules.reporting.agents import ExcelAnalyzerAgent
from src.modules.reporting.models import AgentType
from src.modules.reporting.service import AnalysisService, ResultService

logger = get_logger(__name__)


async def process_analysis_task(
    analysis_id: UUID,
    file_path: str,
    agent_type: AgentType,
    parameters: dict[str, Any] | None = None,
) -> None:
    """
    Process an analysis in the background.

    Args:
        analysis_id: ID of the analysis to process
        file_path: Path to the file in storage
        agent_type: Type of agent to use
        parameters: Optional parameters for the agent
    """
    # Create a new session for this background task
    with SessionLocal() as db:
        analysis_service = AnalysisService(db)
        result_service = ResultService(db)

        try:
            logger.info(
                "Starting analysis processing",
                analysis_id=str(analysis_id),
                agent_type=agent_type.value,
            )

            start_time = time.time()

            # Update analysis status
            analysis_service.update_progress(analysis_id, 0.1, "Initializing analysis agent")

            # Create appropriate agent
            if agent_type == AgentType.EXCEL_ANALYZER:
                agent = ExcelAnalyzerAgent()
            else:
                raise ValueError(f"Unsupported agent type: {agent_type}")

            # Update progress
            analysis_service.update_progress(analysis_id, 0.2, "Loading and analyzing file")

            # Run analysis
            try:
                results = await agent.analyze(file_path, parameters)
            except Exception as e:
                logger.error(
                    "Agent analysis failed",
                    analysis_id=str(analysis_id),
                    error=str(e),
                )
                analysis_service.mark_failed(
                    analysis_id,
                    error_message=f"Analysis failed: {str(e)}",
                    error_details={"agent_error": str(e)},
                )
                return

            # Update progress
            analysis_service.update_progress(analysis_id, 0.8, f"Saving {len(results)} results")

            # Save results in a transaction
            try:
                # Begin transaction for saving all results
                for i, result_data in enumerate(results):
                    result_type = result_data.get("type", "unknown")

                    if result_type == "chart":
                        result_service.create_chart_result(
                            analysis_id=analysis_id,
                            title=result_data.get("title", f"Chart {i + 1}"),
                            chart_type=result_data.get("chart_type", "bar"),
                            chart_data=result_data.get("data", {}),
                            chart_config=result_data.get("config", {}),
                            description=result_data.get("description"),
                            order_index=i,
                            is_primary=(i == 0),
                            display_size=result_data.get("display_size", "medium"),
                        )

                    elif result_type == "insight":
                        result_service.create_insight_result(
                            analysis_id=analysis_id,
                            title=result_data.get("title", f"Insight {i + 1}"),
                            insight_text=result_data.get("content", ""),
                            confidence_score=result_data.get("confidence"),
                            order_index=i,
                            display_size="medium",
                        )

                    else:
                        # Generic result
                        result_service.create_result(
                            analysis_id=analysis_id,
                            result_type=result_type,
                            title=result_data.get("title", f"Result {i + 1}"),
                            description=result_data.get("description"),
                            order_index=i,
                            extra_metadata=result_data,
                        )

                # Commit all results together
                db.commit()

            except Exception as e:
                # Rollback on any error
                db.rollback()
                logger.error(
                    "Failed to save results, rolling back transaction",
                    analysis_id=str(analysis_id),
                    error=str(e),
                    exc_info=True,
                )
                raise

            # Mark analysis as completed
            processing_time = time.time() - start_time
            analysis_service.mark_completed(
                analysis_id,
                processing_time=processing_time,
                tokens_used=None,  # TODO: Track token usage
            )

            logger.info(
                "Analysis completed successfully",
                analysis_id=str(analysis_id),
                processing_time=processing_time,
                results_count=len(results),
            )

        except Exception as e:
            logger.error(
                "Analysis processing failed",
                analysis_id=str(analysis_id),
                error=str(e),
                exc_info=True,
            )

            try:
                analysis_service.mark_failed(
                    analysis_id,
                    error_message="Processing failed due to an unexpected error",
                    error_details={"error": str(e)},
                )
            except Exception as update_error:
                logger.error(
                    "Failed to update analysis status",
                    analysis_id=str(analysis_id),
                    error=str(update_error),
                )


def queue_analysis_processing(
    background_tasks: BackgroundTasks,
    analysis_id: UUID,
    file_path: str,
    agent_type: AgentType,
    parameters: dict[str, Any] | None = None,
) -> None:
    """
    Queue an analysis for background processing.

    Args:
        background_tasks: FastAPI background tasks instance
        analysis_id: ID of the analysis to process
        file_path: Path to the file in storage
        agent_type: Type of agent to use
        parameters: Optional parameters for the agent
    """
    background_tasks.add_task(
        process_analysis_task,
        analysis_id,
        file_path,
        agent_type,
        parameters,
    )
