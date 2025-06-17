"""
Custom exceptions for the application.
"""

from fastapi import HTTPException, status


class BaseError(HTTPException):
    """Base exception class for all custom exceptions."""

    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


# Authentication Errors
class AuthenticationError(BaseError):
    """Authentication related errors."""

    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class PermissionError(BaseError):
    """Permission/Authorization errors."""

    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)


# File Errors
class FileError(BaseError):
    """File processing related errors."""

    pass


class FileNotFoundError(FileError):
    """File not found error."""

    def __init__(self, file_id: str):
        super().__init__(
            detail=f"File with id {file_id} not found", status_code=status.HTTP_404_NOT_FOUND
        )


class InvalidFileTypeError(FileError):
    """Invalid file type error."""

    def __init__(self, file_type: str):
        super().__init__(
            detail=f"Invalid file type: {file_type}. Only Excel files (.xlsx, .xls) are allowed",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class FileTooLargeError(FileError):
    """File size exceeds limit error."""

    def __init__(self, size_mb: float, max_size_mb: int):
        super().__init__(
            detail=f"File size ({size_mb:.1f}MB) exceeds maximum allowed size ({max_size_mb}MB)",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )


# Analysis Errors
class AnalysisError(BaseError):
    """Analysis related errors."""

    pass


class AnalysisNotFoundError(AnalysisError):
    """Analysis not found error."""

    def __init__(self, analysis_id: str):
        super().__init__(
            detail=f"Analysis with id {analysis_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class AnalysisFailedError(AnalysisError):
    """Analysis processing failed error."""

    def __init__(self, reason: str):
        super().__init__(
            detail=f"Analysis failed: {reason}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Resource Errors
class ConflictError(BaseError):
    """Resource conflict errors."""

    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_409_CONFLICT)


# Validation Errors
class ValidationError(BaseError):
    """Input validation errors."""

    def __init__(self, field: str, reason: str):
        super().__init__(
            detail=f"Validation error for field '{field}': {reason}",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


# External Service Errors
class ExternalServiceError(BaseError):
    """External service integration errors."""

    def __init__(self, service: str, reason: str):
        super().__init__(
            detail=f"{service} error: {reason}", status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


class SupabaseError(ExternalServiceError):
    """Supabase specific errors."""

    def __init__(self, reason: str):
        super().__init__(service="Supabase", reason=reason)


class AIServiceError(ExternalServiceError):
    """AI/LLM service errors."""

    def __init__(self, reason: str):
        super().__init__(service="AI Service", reason=reason)
