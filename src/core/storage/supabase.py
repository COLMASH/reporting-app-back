"""
Supabase storage client for file management.
"""

from typing import BinaryIO

from supabase import Client, create_client

from src.core.config import get_settings
from src.core.exceptions import StorageError
from src.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class StorageClient:
    """Supabase storage client for file operations."""

    def __init__(self) -> None:
        """Initialize Supabase client."""
        try:
            if not settings.supabase_url or not settings.supabase_anon_key:
                raise StorageError("Supabase URL and key must be configured")

            self.client: Client = create_client(
                supabase_url=settings.supabase_url,
                supabase_key=settings.supabase_anon_key,
            )
            self.bucket_name = settings.supabase_bucket_name

            if not self.bucket_name:
                raise StorageError("Supabase bucket name must be configured")

            logger.info(
                "Supabase storage client initialized",
                bucket=self.bucket_name,
                url=settings.supabase_url,
            )

            # Ensure bucket exists (this will fail silently if bucket already exists)
            # Using private bucket for signed URL security
            try:
                self.client.storage.create_bucket(self.bucket_name, {"public": False})
            except Exception:
                # Bucket likely already exists, which is fine
                pass

        except Exception as e:
            logger.error("Failed to initialize Supabase client", error=str(e))
            raise StorageError(f"Failed to connect to storage service: {str(e)}") from e

    async def upload_file(
        self,
        file_path: str,
        file_content: bytes | BinaryIO,
        content_type: str | None = None,
    ) -> str:
        """
        Upload a file to Supabase storage.

        Args:
            file_path: Path where file will be stored in bucket
            file_content: File content as binary stream
            content_type: MIME type of the file

        Returns:
            Public URL of the uploaded file

        Raises:
            StorageError: If upload fails
        """
        try:
            # Check if bucket is initialized
            if not self.bucket_name:
                raise StorageError("Storage bucket not configured")

            # Upload to Supabase
            # Note: Supabase client expects bytes, not BinaryIO
            if hasattr(file_content, "read"):
                # If it's a file-like object, read it
                file_data = file_content.read()
            else:
                # It's already bytes
                file_data = file_content

            # Ensure file_data is bytes
            if isinstance(file_data, str):
                file_data = file_data.encode("utf-8")

            # First, try to remove the file if it exists (to handle duplicates)
            try:
                self.client.storage.from_(self.bucket_name).remove([file_path])
            except Exception:
                # File might not exist, which is fine
                pass

            # Now upload the file
            # Using the basic upload method without options to avoid the response error
            storage_client = self.client.storage.from_(self.bucket_name)
            storage_client.upload(file_path, file_data)

            # Get public URL
            public_url = storage_client.get_public_url(file_path)

            logger.info("File uploaded successfully", file_path=file_path, public_url=public_url)
            return str(public_url)

        except Exception as e:
            error_msg = str(e)
            logger.error("File upload failed", file_path=file_path, error=error_msg)

            # If it's the specific "response" error, provide more context
            if "cannot access local variable 'response'" in error_msg:
                raise StorageError("Upload failed due to Supabase client error. " "Please check Supabase configuration and bucket permissions.") from e

            raise StorageError(f"Failed to upload file: {error_msg}") from e

    async def delete_file(self, file_path: str) -> None:
        """
        Delete a file from Supabase storage.

        Args:
            file_path: Path of the file in the bucket

        Raises:
            StorageError: If deletion fails
        """
        try:
            self.client.storage.from_(self.bucket_name).remove([file_path])
            logger.info("File deleted successfully", file_path=file_path)

        except Exception as e:
            logger.error("File deletion failed", file_path=file_path, error=str(e))
            raise StorageError(f"Failed to delete file: {str(e)}") from e

    async def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            file_path: Path of the file in the bucket

        Returns:
            True if file exists, False otherwise
        """
        try:
            # List files in the directory
            directory = "/".join(file_path.split("/")[:-1])
            filename = file_path.split("/")[-1]

            response = self.client.storage.from_(self.bucket_name).list(path=directory, options={"limit": 100})

            # Check if our file is in the list
            return any(file["name"] == filename for file in response)

        except Exception as e:
            logger.error("Failed to check file existence", file_path=file_path, error=str(e))
            return False

    def get_public_url(self, file_path: str) -> str:
        """
        Get public URL for a file.

        Args:
            file_path: Path of the file in the bucket

        Returns:
            Public URL of the file
        """
        return str(self.client.storage.from_(self.bucket_name).get_public_url(file_path))

    def create_signed_url(self, file_path: str, expires_in: int = 3600) -> dict[str, str | None]:
        """
        Create a signed URL for secure, time-limited file access.

        Args:
            file_path: Path of the file in the bucket
            expires_in: URL expiration time in seconds (default: 3600 = 1 hour)

        Returns:
            Dictionary containing signedURL key with the signed URL string

        Raises:
            StorageError: If signed URL creation fails
        """
        try:
            response = self.client.storage.from_(self.bucket_name).create_signed_url(path=file_path, expires_in=expires_in)

            if response.get("error"):
                raise StorageError(f"Failed to create signed URL: {response['error']}")

            logger.info("Signed URL created successfully", file_path=file_path, expires_in=expires_in)

            return {"signedURL": response.get("signedURL")}

        except Exception as e:
            logger.error("Failed to create signed URL", file_path=file_path, expires_in=expires_in, error=str(e))
            raise StorageError(f"Failed to create signed URL: {str(e)}") from e


# Global storage client instance
_storage_client: StorageClient | None = None


def get_storage_client() -> StorageClient:
    """Get or create storage client instance."""
    global _storage_client
    if _storage_client is None:
        _storage_client = StorageClient()
    return _storage_client
