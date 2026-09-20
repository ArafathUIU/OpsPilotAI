"""Database engine, session factory, and infrastructure health check utilities."""

from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import get_settings
from src.observability.logging import get_logger
from src.persistence.models.base import Base

logger = get_logger(__name__)
settings = get_settings()


# Engine creation
def create_engine_instance() -> AsyncEngine:
    db_url = settings.DATABASE_URL
    if settings.USE_SQLITE_FALLBACK:
        db_url = settings.SQLITE_URL

    # SQLite requires specific connect_args for multithreading
    connect_args = {}
    if "sqlite" in db_url:
        connect_args["check_same_thread"] = False

    return create_async_engine(
        db_url,
        echo=settings.DEBUG and settings.ENVIRONMENT == "development",
        future=True,
        connect_args=connect_args,
    )


engine: AsyncEngine = create_engine_instance()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for obtaining an isolated async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Creates database tables from Base metadata (useful for tests or standalone runs)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized successfully.")


async def check_db_health() -> bool:
    """Verifies that the database engine can successfully execute a query."""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as exc:
        logger.error(f"Database health check failed: {exc}")
        return False


async def check_redis_health() -> bool:
    """Verifies connectivity to the Redis instance."""
    try:
        client = aioredis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=2,
            decode_responses=True,
        )
        ping_res = await client.ping()
        await client.aclose()
        return ping_res is True
    except Exception as exc:
        logger.warning(f"Redis health check failed (optional in development mode): {exc}")
        return False
