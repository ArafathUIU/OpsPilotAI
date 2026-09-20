"""Centralized application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core Application
    PROJECT_NAME: str = "OpsPilot AI"
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # PostgreSQL & pgvector
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "opspilot"
    POSTGRES_PASSWORD: str = "opspilot_secret_password"
    POSTGRES_DB: str = "opspilot_db"
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://opspilot:opspilot_secret_password@localhost:5432/opspilot_db",
        description="Async SQLAlchemy database connection string",
    )
    SQLITE_URL: str = "sqlite+aiosqlite:///./opspilot_dev.db"
    USE_SQLITE_FALLBACK: bool = False

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM Providers
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_FAST_MODEL: str = "gpt-4o-mini"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Security
    SECRET_KEY: str = "ops-pilot-super-secret-production-quality-signing-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Safety & Budgets
    MAX_AGENT_ITERATIONS: int = 3
    MAX_INCIDENT_TOKENS: int = 50000
    MAX_RETRIEVED_DOCUMENTS: int = 3
    DEFAULT_INVESTIGATION_TIMEOUT_SECONDS: int = 60

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_async_db_url(cls, v: str | None) -> str:
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return (
            v or "postgresql+asyncpg://opspilot:opspilot_secret_password@localhost:5432/opspilot_db"
        )


@lru_cache
def get_settings() -> Settings:
    """Returns cached application settings instance."""
    return Settings()
