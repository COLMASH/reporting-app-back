"""
Application configuration using pydantic-settings.
"""

import json

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = Field(default="Reporting Backend", description="Application name")
    environment: str = Field(
        default="development", description="Environment (development, staging, production)"
    )
    debug: bool = Field(default=False, description="Debug mode", alias="APP_DEBUG")
    log_level: str = Field(default="INFO", description="Logging level")

    # Database
    database_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/reporting_dev",
        description="PostgreSQL connection string",
    )

    # Supabase
    supabase_url: str = Field(
        default="https://placeholder.supabase.co", description="Supabase project URL"
    )
    supabase_anon_key: str = Field(default="placeholder-key", description="Supabase anonymous key")
    supabase_service_key: str | None = Field(
        default=None, description="Supabase service key (optional)"
    )

    # Authentication
    jwt_secret: str = Field(
        default="development-secret-key-change-in-production", description="JWT secret key"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_minutes: int = Field(default=30, description="JWT token expiration in minutes")

    # CORS
    backend_cors_origins: list[str] = Field(
        default=["http://localhost:3000"], description="Allowed CORS origins"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379", description="Redis connection URL")

    # AI/LLM
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    langchain_api_key: str | None = Field(default=None, description="LangChain/LangSmith API key")
    langchain_tracing_v2: bool = Field(default=False, description="Enable LangChain tracing")
    langchain_project: str = Field(
        default="reporting-backend", description="LangChain project name"
    )

    # File Upload
    max_upload_size_mb: int = Field(default=50, description="Maximum file upload size in MB")
    allowed_extensions: list[str] = Field(
        default=[".xlsx", ".xls"], description="Allowed file extensions"
    )

    # Rate Limiting
    rate_limit_requests: int = Field(default=100, description="Rate limit requests per period")
    rate_limit_period: int = Field(default=60, description="Rate limit period in seconds")

    # Monitoring
    sentry_dsn: str | None = Field(default=None, description="Sentry DSN for error tracking")
    prometheus_enabled: bool = Field(default=False, description="Enable Prometheus metrics")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
                return [str(parsed)]
            except json.JSONDecodeError:
                return [v]
        if isinstance(v, list):
            return [str(item) for item in v]
        return [str(v)]

    @field_validator("allowed_extensions", mode="before")
    @classmethod
    def parse_allowed_extensions(cls, v: str | list[str]) -> list[str]:
        """Parse allowed extensions from string or list."""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
                return [str(parsed)]
            except json.JSONDecodeError:
                return [v]
        if isinstance(v, list):
            return [str(item) for item in v]
        return [str(v)]

    @property
    def max_upload_size_bytes(self) -> int:
        """Get max upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"


# Create global settings instance
# Pydantic settings will load from environment variables or .env file
settings = Settings()
