"""
Reporting module endpoints for file upload, analysis, and results.
"""

import os
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, status

from src.core.decorators.logging import log_endpoint
from src.core.exceptions import StorageError
from src.core.storage import get_storage_client
from src.modules.auth.dependencies import CurrentUser
from src.modules.reporting import schemas
from src.modules.reporting.dependencies import (
    AnalysisServiceDep,
    FileServiceDep,
    ResultServiceDep,
    ValidatedFile,
)
from src.modules.reporting.models import AgentType, DataClassification
from src.modules.reporting.tasks import queue_analysis_processing

router = APIRouter(prefix="/reporting", tags=["reporting"])


# File Upload Endpoints
@router.post("/files/upload", response_model=schemas.FileUploadResponse)
@log_endpoint
async def upload_file(
    file: ValidatedFile,
    current_user: CurrentUser,
    file_service: FileServiceDep,
    company_name: Annotated[str | None, Form()] = None,
    department: Annotated[str | None, Form()] = None,
    classification: Annotated[str | None, Form()] = None,
) -> schemas.FileUploadResponse:
    """
    Upload an Excel file for processing.

    This endpoint handles Excel file uploads for subsequent analysis. Files are
    validated for type and size, then stored in Supabase storage with metadata
    tracked in the database.

    Args:
        file: Excel file (.xlsx or .xls) - validated for type and size
        company_name: Company name for the file (defaults to user's company)
        department: Department name (optional)
        classification: Data classification - valid values: portfolio, operations,
                       project_management, finance, other (defaults to 'other' if invalid)

    Returns:
        FileUploadResponse with file ID and upload status

    Raises:
        400: Invalid file type or file too large
        503: Storage service unavailable
        500: Unexpected server error
    """
    try:
        # Generate unique file path
        file_id = uuid4()
        filename = file.filename or "unknown.xlsx"
        file_extension = os.path.splitext(filename)[1]
        storage_path = f"{current_user.id}/{file_id}{file_extension}"

        # Upload to Supabase
        storage_client = get_storage_client()
        file_content = await file.read()
        await storage_client.upload_file(
            file_path=storage_path,
            file_content=file_content,
            content_type=file.content_type,
        )

        # Create metadata record
        # Handle classification - validate against enum values
        data_classification = None
        if classification:
            try:
                data_classification = DataClassification(classification.lower())
            except ValueError:
                # Invalid classification, default to OTHER
                data_classification = DataClassification.OTHER

        file_metadata = file_service.create_file_metadata(
            user_id=current_user.id,
            filename=f"{file_id}{file_extension}",
            original_filename=filename,
            supabase_path=storage_path,
            supabase_bucket=storage_client.bucket_name,
            company_name=company_name or getattr(current_user, "company_name", None) or "Unknown",
            department=department,
            data_classification=data_classification,
            file_size=len(file_content),
            mime_type=file.content_type,
        )

        return schemas.FileUploadResponse(
            id=str(file_metadata.id),
            filename=file_metadata.filename,
            status=file_metadata.status.value,
            message="File uploaded successfully",
        )

    except StorageError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file due to an unexpected error",
        ) from e


@router.get("/files", response_model=list[schemas.FileInfo])
@log_endpoint
async def list_files(
    current_user: CurrentUser,
    file_service: FileServiceDep,
) -> list[schemas.FileInfo]:
    """
    List all files uploaded by the current user.

    Returns files ordered by upload date (newest first), including
    file metadata and processing status.

    Returns:
        List of FileInfo objects with file details
    """
    files = file_service.get_user_files(current_user.id)
    return [schemas.FileInfo.model_validate(file) for file in files]


@router.get("/files/{file_id}", response_model=schemas.FileInfo)
@log_endpoint
async def get_file_info(
    file_id: UUID,
    current_user: CurrentUser,
    file_service: FileServiceDep,
) -> schemas.FileInfo:
    """
    Get detailed information about a specific file.

    Args:
        file_id: UUID of the file to retrieve

    Returns:
        FileInfo with complete file metadata

    Raises:
        404: File not found or access denied
    """
    file = file_service.get_file(file_id, current_user.id)
    return schemas.FileInfo.model_validate(file)


@router.delete("/files/{file_id}")
@log_endpoint
async def delete_file(
    file_id: UUID,
    current_user: CurrentUser,
    file_service: FileServiceDep,
) -> dict[str, str]:
    """
    Delete a file and all associated analyses.

    This operation will:
    1. Delete the file from Supabase storage
    2. Delete the file metadata from database
    3. Cascade delete all analyses and results

    Args:
        file_id: UUID of the file to delete

    Returns:
        Success message

    Raises:
        404: File not found or access denied
    """
    await file_service.delete_file(file_id, current_user.id)
    return {"message": "File deleted successfully"}


# Analysis Endpoints
@router.post("/analysis", response_model=schemas.AnalysisResponse)
@log_endpoint
async def create_analysis(
    request: schemas.AnalysisRequest,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    file_service: FileServiceDep,
    analysis_service: AnalysisServiceDep,
) -> schemas.AnalysisResponse:
    """
    Create a new analysis job for a file.

    Queues an analysis job for background processing. The analysis will
    be processed asynchronously using the specified agent type.

    Args:
        request: Analysis configuration including file_id, agent_type, and parameters

    Returns:
        AnalysisResponse with analysis ID and initial status

    Raises:
        404: File not found or access denied
        400: Invalid agent type or parameters
    """
    # Verify file exists and get its path
    file = file_service.get_file(request.file_id, current_user.id)

    # Create analysis record
    analysis = analysis_service.create_analysis(
        file_id=request.file_id,
        agent_type=AgentType(request.agent_type),
        user_id=current_user.id,
        parameters=request.parameters,
    )

    # Queue background processing
    queue_analysis_processing(
        background_tasks,
        analysis.id,
        str(file.supabase_path),
        analysis.agent_type,
        request.parameters,
    )

    return schemas.AnalysisResponse(
        id=str(analysis.id),
        file_id=analysis.file_id,
        status=analysis.status.value,
        agent_type=analysis.agent_type.value,
        message="Analysis queued for processing",
    )


@router.get("/analysis/{analysis_id}", response_model=schemas.AnalysisInfo)
@log_endpoint
async def get_analysis_status(
    analysis_id: UUID,
    current_user: CurrentUser,
    analysis_service: AnalysisServiceDep,
) -> schemas.AnalysisInfo:
    """
    Get analysis status and progress.

    Check the current status of an analysis job, including progress
    percentage and any error messages.

    Args:
        analysis_id: UUID of the analysis to check

    Returns:
        AnalysisInfo with current status and progress

    Raises:
        404: Analysis not found or access denied
    """
    analysis = analysis_service.get_analysis(analysis_id, current_user.id)
    return schemas.AnalysisInfo.model_validate(analysis)


@router.get("/analysis/by-file/{file_id}", response_model=list[schemas.AnalysisInfo])
@log_endpoint
async def get_file_analyses(
    file_id: UUID,
    current_user: CurrentUser,
    analysis_service: AnalysisServiceDep,
) -> list[schemas.AnalysisInfo]:
    """
    Get all analyses for a specific file.

    Returns all analysis jobs associated with a file, ordered by
    creation date (newest first).

    Args:
        file_id: UUID of the file

    Returns:
        List of AnalysisInfo objects

    Raises:
        404: File not found or access denied
    """
    analyses = analysis_service.get_file_analyses(file_id, current_user.id)
    return [schemas.AnalysisInfo.model_validate(a) for a in analyses]


@router.delete("/analysis/{analysis_id}")
@log_endpoint
async def cancel_analysis(
    analysis_id: UUID,
    current_user: CurrentUser,
    analysis_service: AnalysisServiceDep,
) -> dict[str, str]:
    """
    Cancel a pending or in-progress analysis job.

    Only pending or in-progress analyses can be cancelled. Completed
    or failed analyses cannot be cancelled.

    Args:
        analysis_id: UUID of the analysis to cancel

    Returns:
        Success message

    Raises:
        400: Analysis already completed or failed
        404: Analysis not found or access denied
    """
    analysis = analysis_service.get_analysis(analysis_id, current_user.id)

    if analysis.status.value in ["completed", "failed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel completed or failed analysis",
        )

    analysis_service.mark_failed(
        analysis_id,
        "Analysis cancelled by user",
        {"cancelled_by": str(current_user.id)},
    )

    return {"message": "Analysis cancelled successfully"}


# Results Endpoints
@router.get("/results/by-analysis/{analysis_id}", response_model=list[schemas.ResultDetail])
@log_endpoint
async def get_analysis_results(
    analysis_id: UUID,
    current_user: CurrentUser,
    result_service: ResultServiceDep,
) -> list[schemas.ResultDetail]:
    """
    Get all results for a completed analysis.

    Returns results in the order they were created, including charts
    and insights generated by the analysis.

    Args:
        analysis_id: UUID of the analysis

    Returns:
        List of ResultDetail objects ordered by display order

    Raises:
        404: Analysis not found or access denied
    """
    results = result_service.get_analysis_results(analysis_id, current_user.id)
    return [schemas.ResultDetail.model_validate(r) for r in results]


@router.get("/results/{result_id}", response_model=schemas.ResultDetail)
@log_endpoint
async def get_result_detail(
    result_id: UUID,
    current_user: CurrentUser,
    result_service: ResultServiceDep,
) -> schemas.ResultDetail:
    """
    Get detailed information for a specific result.

    Retrieves complete result data including chart configurations
    or insight text.

    Args:
        result_id: UUID of the result

    Returns:
        ResultDetail with complete result data

    Raises:
        404: Result not found or access denied
    """
    result = result_service.get_result(result_id, current_user.id)
    return schemas.ResultDetail.model_validate(result)


# Combined Endpoints
@router.get("/files/{file_id}/complete", response_model=schemas.FileWithAnalyses)
@log_endpoint
async def get_file_with_analyses(
    file_id: UUID,
    current_user: CurrentUser,
    file_service: FileServiceDep,
    analysis_service: AnalysisServiceDep,
) -> schemas.FileWithAnalyses:
    """
    Get file information with all associated analyses.

    Convenience endpoint that returns file metadata along with
    all analysis jobs in a single response.

    Args:
        file_id: UUID of the file

    Returns:
        FileWithAnalyses containing file info and analysis list

    Raises:
        404: File not found or access denied
    """
    file = file_service.get_file(file_id, current_user.id)
    analyses = analysis_service.get_file_analyses(file_id, current_user.id)

    return schemas.FileWithAnalyses(
        file=schemas.FileInfo.model_validate(file),
        analyses=[schemas.AnalysisInfo.model_validate(a) for a in analyses],
    )


@router.get("/analysis/{analysis_id}/complete", response_model=schemas.AnalysisWithResults)
@log_endpoint
async def get_analysis_with_results(
    analysis_id: UUID,
    current_user: CurrentUser,
    analysis_service: AnalysisServiceDep,
    result_service: ResultServiceDep,
) -> schemas.AnalysisWithResults:
    """
    Get analysis information with all results.

    Convenience endpoint that returns analysis metadata along with
    all generated results in a single response.

    Args:
        analysis_id: UUID of the analysis

    Returns:
        AnalysisWithResults containing analysis info and results list

    Raises:
        404: Analysis not found or access denied
    """
    analysis = analysis_service.get_analysis(analysis_id, current_user.id)
    results = result_service.get_analysis_results(analysis_id, current_user.id)

    return schemas.AnalysisWithResults(
        analysis=schemas.AnalysisInfo.model_validate(analysis),
        results=[schemas.ResultDetail.model_validate(r) for r in results],
    )
