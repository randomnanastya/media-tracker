from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any, cast

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.responses import Response
from httpx import Request

from app.api import jellyfin, radarr, sonarr
from app.config import logger
from app.exceptions.handlers import register_exception_handlers
from app.services.jobs import (
    jellyfin_import_users_job,
    jellyfin_sync_movies_job,
    radarr_import_job,
    sonarr_import_job,
)

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    """Startup/shutdown lifecycle with APScheduler."""
    try:
        jobs = [
            ("Jellyfin Users", "1:00"),
            ("Radarr", "1:10"),
            ("Jellyfin Movies", "1:30"),
            ("Sonarr", "2:00"),
        ]

        for name, time in jobs:
            logger.info("📅 Scheduled %s at %s UTC", name, time)

        scheduler.add_job(
            jellyfin_import_users_job,
            "cron",
            hour=1,
            minute=0,
            id="jellyfin_users_import",
            misfire_grace_time=300,
            coalesce=True,
        )

        scheduler.add_job(radarr_import_job, "cron", hour=1, minute=10, id="radarr_import")

        scheduler.add_job(
            jellyfin_sync_movies_job, "cron", hour=1, minute=30, id="sync_jellyfin_movies"
        )

        scheduler.add_job(sonarr_import_job, "cron", hour=2, minute=0, id="sonarr_import")

        scheduler.start()
        logger.info("✅ Scheduler started with misfire_grace_time=300")

        for job in scheduler.get_jobs():
            logger.info("⏰ Next run for %s: %s", job.id, job.next_run_time)

    except Exception as e:
        logger.exception("Failed to start scheduler: %s", e)

    yield

    try:
        scheduler.shutdown(wait=False)
        logger.info("🛑 Scheduler stopped")
    except Exception as e:
        logger.exception("Failed to stop scheduler cleanly: %s", e)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Media Tracker API",
        description="Collects and stores stats from Sonarr, Radarr, and Jellyfin",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Include routers
    app.include_router(radarr.router)
    app.include_router(sonarr.router)
    app.include_router(jellyfin.router)

    # Register exception handlers
    register_exception_handlers(app)

    return app


# Create app instance
app: FastAPI = create_app()


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Media Tracker API is running"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.middleware("http")
async def log_requests(request: Request, call_next: Callable[[Request], Any]) -> Response:
    """Middleware for logging HTTP requests and responses."""
    logger.info("Request to %s: method=%s", request.url.path, request.method)
    response = await call_next(request)
    logger.info("Response for %s: status=%s", request.url.path, response.status_code)
    return cast(Response, response)
