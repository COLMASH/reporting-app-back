"""
Anthropic file storage functions for file management.
"""

import anthropic

from src.core.config import get_settings
from src.core.exceptions import StorageError
from src.core.logging import get_logger

logger = get_logger(__name__)

# Global client instance
_anthropic_client: anthropic.Anthropic | None = None


def get_anthropic_client() -> anthropic.Anthropic:
    """Get or create Anthropic client instance."""
    global _anthropic_client

    if _anthropic_client is None:
        settings = get_settings()

        if not settings.anthropic_api_key:
            raise StorageError("Anthropic API key not configured")

        _anthropic_client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
            default_headers={"anthropic-beta": "files-api-2025-04-14"},
        )
        logger.info("Anthropic client initialized")

    return _anthropic_client


async def upload_file_to_anthropic(
    file_content: bytes,
    filename: str,
) -> str:
    """
    Upload a file to Anthropic.

    Args:
        file_content: File content as bytes
        filename: Name of the file

    Returns:
        Anthropic file ID

    Raises:
        StorageError: If upload fails
    """
    try:
        client = get_anthropic_client()

        # Upload file to Anthropic
        # The file parameter expects a tuple of (filename, file_content)
        response = client.beta.files.upload(
            file=(filename, file_content),
        )

        logger.info(
            "File uploaded to Anthropic",
            file_id=response.id,
            filename=filename,
        )

        return response.id

    except Exception as e:
        logger.error(
            "Failed to upload file to Anthropic",
            filename=filename,
            error=str(e),
        )
        raise StorageError(f"Failed to upload file to Anthropic: {str(e)}") from e


async def delete_file_from_anthropic(file_id: str) -> None:
    """
    Delete a file from Anthropic.

    Args:
        file_id: Anthropic file ID

    Raises:
        StorageError: If deletion fails
    """
    try:
        client = get_anthropic_client()
        client.beta.files.delete(file_id)
        logger.info("File deleted from Anthropic", file_id=file_id)

    except Exception as e:
        logger.error(
            "Failed to delete file from Anthropic",
            file_id=file_id,
            error=str(e),
        )
        raise StorageError(f"Failed to delete file from Anthropic: {str(e)}") from e
