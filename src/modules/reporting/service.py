"""
Business logic for reporting module.
"""

import os
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from src.core.exceptions import NotFoundError, StorageError, ValidationError
from src.core.logging import get_logger
from src.core.storage import get_storage_client
from src.modules.reporting.models import (
    AgentType,
    Analysis,
    AnalysisStatus,
    ChartType,
    FileStatus,
    FileUpload,
    Result,
)


class FileService:
    """Handle file upload operations and metadata management."""

    def __init__(self, db: Session):
        self.db = db
        self.logger = get_logger(__name__)
        self.storage = get_storage_client()

    def create_file_metadata(
        self,
        user_id: UUID,
        filename: str,
        original_filename: str,
        supabase_path: str,
        company_name: str,
        **kwargs: Any,
    ) -> FileUpload:
        """Create file metadata record after successful Supabase upload."""
        file_upload = FileUpload(
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

        self.db.add(file_upload)
        self.db.commit()
        self.db.refresh(file_upload)

        self.logger.info(
            "File metadata created",
            file_id=str(file_upload.id),
            user_id=str(user_id),
            filename=filename,
        )

        return file_upload

    def get_user_files(self, user_id: UUID) -> list[FileUpload]:
        """Get all files for a user."""
        files = (
            self.db.query(FileUpload)
            .filter(FileUpload.user_id == user_id)
            .order_by(FileUpload.created_at.desc())
            .all()
        )
        return files

    def get_file(self, file_id: UUID, user_id: UUID) -> FileUpload:
        """Get file by ID, ensuring user ownership."""
        file = (
            self.db.query(FileUpload)
            .filter(FileUpload.id == file_id, FileUpload.user_id == user_id)
            .first()
        )

        if not file:
            raise NotFoundError(f"File {file_id}")

        return file

    async def delete_file(self, file_id: UUID, user_id: UUID) -> None:
        """Delete file and all associated data."""
        file = self.get_file(file_id, user_id)

        # Delete from Supabase storage
        try:
            await self.storage.delete_file(str(file.supabase_path))
        except StorageError as e:
            self.logger.error(
                "Failed to delete file from storage",
                file_id=str(file_id),
                error=str(e),
            )
            # Continue with database deletion even if storage deletion fails

        # Delete from database (cascade will handle analyses and results)
        self.db.delete(file)
        self.db.commit()

        self.logger.info(
            "File deleted",
            file_id=str(file_id),
            user_id=str(user_id),
        )


class AnalysisService:
    """Handle analysis job creation and management."""

    def __init__(self, db: Session):
        self.db = db
        self.logger = get_logger(__name__)

    def create_analysis(
        self,
        file_id: UUID,
        agent_type: AgentType,
        user_id: UUID,
        parameters: dict[str, Any] | None = None,
    ) -> Analysis:
        """Create a new analysis job."""
        # Verify file exists and belongs to user
        file = (
            self.db.query(FileUpload)
            .filter(FileUpload.id == file_id, FileUpload.user_id == user_id)
            .first()
        )

        if not file:
            raise NotFoundError(f"File {file_id}")

        analysis = Analysis(
            id=uuid4(),
            file_id=file_id,
            agent_type=agent_type,
            parameters=parameters,
            status=AnalysisStatus.PENDING,
        )

        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        self.logger.info(
            "Analysis created",
            analysis_id=str(analysis.id),
            file_id=str(file_id),
            agent_type=agent_type.value,
        )

        # Note: Background task should be queued by the controller/endpoint
        # that has access to FastAPI's BackgroundTasks

        return analysis

    def get_analysis(self, analysis_id: UUID, user_id: UUID) -> Analysis:
        """Get analysis by ID, ensuring user ownership."""
        analysis = (
            self.db.query(Analysis)
            .join(FileUpload)
            .filter(Analysis.id == analysis_id, FileUpload.user_id == user_id)
            .first()
        )

        if not analysis:
            raise NotFoundError(f"Analysis {analysis_id}")

        return analysis

    def get_file_analyses(self, file_id: UUID, user_id: UUID) -> list[Analysis]:
        """Get all analyses for a file."""
        analyses = (
            self.db.query(Analysis)
            .join(FileUpload)
            .filter(Analysis.file_id == file_id, FileUpload.user_id == user_id)
            .order_by(Analysis.created_at.desc())
            .all()
        )
        return analyses

    def update_progress(
        self, analysis_id: UUID, progress: float, message: str | None = None
    ) -> None:
        """Update analysis progress."""
        analysis = self.db.query(Analysis).filter(Analysis.id == analysis_id).first()

        if not analysis:
            raise NotFoundError(f"Analysis {analysis_id}")

        analysis.progress = progress
        analysis.progress_message = message

        if analysis.status == AnalysisStatus.PENDING:
            analysis.status = AnalysisStatus.IN_PROGRESS
            analysis.started_at = datetime.now(UTC)

        self.db.commit()

        self.logger.info(
            "Analysis progress updated",
            analysis_id=str(analysis_id),
            progress=progress,
        )

    def mark_completed(
        self,
        analysis_id: UUID,
        processing_time: float | None = None,
        tokens_used: int | None = None,
    ) -> None:
        """Mark analysis as completed."""
        analysis = self.db.query(Analysis).filter(Analysis.id == analysis_id).first()

        if not analysis:
            raise NotFoundError(f"Analysis {analysis_id}")

        analysis.status = AnalysisStatus.COMPLETED
        analysis.progress = 1.0
        analysis.completed_at = datetime.now(UTC)
        analysis.processing_time_seconds = processing_time
        analysis.tokens_used = tokens_used

        self.db.commit()

        self.logger.info(
            "Analysis completed",
            analysis_id=str(analysis_id),
            processing_time=processing_time,
            tokens_used=tokens_used,
        )

    def mark_failed(
        self, analysis_id: UUID, error_message: str, error_details: dict[str, Any] | None = None
    ) -> None:
        """Mark analysis as failed."""
        analysis = self.db.query(Analysis).filter(Analysis.id == analysis_id).first()

        if not analysis:
            raise NotFoundError(f"Analysis {analysis_id}")

        analysis.status = AnalysisStatus.FAILED
        analysis.error_message = error_message
        analysis.error_details = error_details
        analysis.completed_at = datetime.now(UTC)

        self.db.commit()

        self.logger.error(
            "Analysis failed",
            analysis_id=str(analysis_id),
            error_message=error_message,
        )


class ResultService:
    """Handle analysis results storage and retrieval."""

    def __init__(self, db: Session):
        self.db = db
        self.logger = get_logger(__name__)

    def create_result(
        self, analysis_id: UUID, result_type: str, title: str, **kwargs: Any
    ) -> Result:
        """Create a new result."""
        # Get current max order index for this analysis
        max_order = (
            self.db.query(Result.order_index)
            .filter(Result.analysis_id == analysis_id)
            .order_by(Result.order_index.desc())
            .first()
        )
        next_order = (max_order[0] + 1) if max_order else 0

        result = Result(
            id=uuid4(),
            analysis_id=analysis_id,
            result_type=result_type,
            title=title,
            order_index=kwargs.pop("order_index", next_order),
            **kwargs,
        )

        self.db.add(result)
        self.db.flush()  # Flush to get ID but don't commit yet
        self.db.refresh(result)

        self.logger.info(
            "Result created",
            result_id=str(result.id),
            analysis_id=str(analysis_id),
            result_type=result_type,
        )

        return result

    def create_chart_result(
        self,
        analysis_id: UUID,
        title: str,
        chart_type: str,
        chart_data: dict[str, Any],
        chart_config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Result:
        """Create a chart result with Chart.js compatible data."""
        return self.create_result(
            analysis_id=analysis_id,
            result_type="chart",
            title=title,
            chart_type=ChartType(chart_type),
            chart_data=chart_data,
            chart_config=chart_config or {},
            **kwargs,
        )

    def create_insight_result(
        self,
        analysis_id: UUID,
        title: str,
        insight_text: str,
        confidence_score: float | None = None,
        **kwargs: Any,
    ) -> Result:
        """Create an insight result."""
        return self.create_result(
            analysis_id=analysis_id,
            result_type="insight",
            title=title,
            insight_text=insight_text,
            confidence_score=confidence_score,
            **kwargs,
        )

    def get_analysis_results(self, analysis_id: UUID, user_id: UUID) -> list[Result]:
        """Get all results for an analysis."""
        results = (
            self.db.query(Result)
            .join(Analysis)
            .join(FileUpload)
            .filter(Result.analysis_id == analysis_id, FileUpload.user_id == user_id)
            .order_by(Result.order_index)
            .all()
        )
        return results

    def get_result(self, result_id: UUID, user_id: UUID) -> Result:
        """Get result by ID, ensuring user ownership."""
        result = (
            self.db.query(Result)
            .join(Analysis)
            .join(FileUpload)
            .filter(Result.id == result_id, FileUpload.user_id == user_id)
            .first()
        )

        if not result:
            raise NotFoundError(f"Result {result_id}")

        return result


class ReportingOrchestrator:
    """Coordinate the complete reporting workflow."""

    def __init__(
        self,
        file_service: FileService,
        analysis_service: AnalysisService,
        result_service: ResultService,
    ):
        self.file_service = file_service
        self.analysis_service = analysis_service
        self.result_service = result_service

    async def process_excel_analysis(
        self,
        file_id: UUID,
        user_id: UUID,
        agent_type: AgentType = AgentType.EXCEL_ANALYZER,
        parameters: dict[str, Any] | None = None,
    ) -> Analysis:
        """
        Orchestrate the complete Excel analysis workflow.

        1. Validate file exists and belongs to user
        2. Create analysis job
        3. Queue background processing
        4. Return analysis tracking info
        """
        # Validate file exists and belongs to user
        file = self.file_service.get_file(file_id, user_id)

        if file.status != FileStatus.UPLOADED:
            raise ValidationError(
                "file_status",
                f"File {file_id} is not ready for analysis. Current status: {file.status.value}",
            )

        # Create analysis job
        analysis = self.analysis_service.create_analysis(
            file_id=file_id,
            agent_type=agent_type,
            user_id=user_id,
            parameters=parameters,
        )

        # TODO: Queue background processing task
        # For now, we'll return the analysis in pending state
        # Background task will process it asynchronously

        return analysis
