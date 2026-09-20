"""FastAPI application entrypoint for OpsPilot AI."""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes.health import router as health_router
from src.core.config import get_settings
from src.observability.logging import get_logger, setup_logging
from src.persistence.session import check_db_health, init_db

settings = get_settings()
setup_logging(settings.LOG_LEVEL)
logger = get_logger("opspilot.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for application startup and graceful shutdown."""
    logger.info(
        f"Starting {settings.PROJECT_NAME} in [{settings.ENVIRONMENT}] mode",
        extra={"environment": settings.ENVIRONMENT, "debug": settings.DEBUG},
    )

    # In SQLite fallback or testing mode, auto-create tables if needed
    if settings.USE_SQLITE_FALLBACK or "sqlite" in settings.DATABASE_URL:
        await init_db()
    else:
        # Check PostgreSQL connectivity
        is_healthy = await check_db_health()
        if not is_healthy:
            logger.warning(
                "PostgreSQL is not currently reachable. The application will start, but database "
                "operations will fail until Postgres is running."
            )

    yield

    logger.info(f"Shutting down {settings.PROJECT_NAME} gracefully.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Autonomous Multi-Agent Incident Response & Root Cause Analysis Platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    """Logs incoming HTTP requests and latency in structured format."""
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Avoid logging health checks to reduce noise
    if not request.url.path.endswith("/health"):
        logger.info(
            f"{request.method} {request.url.path} returned {response.status_code} "
            f"in {duration_ms}ms",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
    return response


# Include health and readiness router
app.include_router(health_router)

# Mount API v1 router prefix placeholder
api_v1_router = FastAPI()
app.mount(settings.API_V1_STR, api_v1_router)
