"""Unit tests for centralized configuration settings."""

from src.core.config import Settings


def test_default_settings():
    settings = Settings()
    assert settings.PROJECT_NAME == "OpsPilot AI"
    assert settings.ENVIRONMENT in ["development", "staging", "production", "test"]
    assert settings.PORT == 8000
    assert "postgresql+asyncpg://" in settings.DATABASE_URL
    assert settings.MAX_AGENT_ITERATIONS == 3


def test_database_url_validation_replaces_sync_scheme():
    sync_url = "postgresql://user:pass@localhost:5432/testdb"
    settings = Settings(DATABASE_URL=sync_url)
    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/testdb"
