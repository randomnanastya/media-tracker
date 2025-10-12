from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from app.api import radarr
from app.core.logging import logger
from app.database import AsyncSessionLocal  # <- импортируем рабочий get_session
from app.services.radarr_service import import_radarr_movies

scheduler = AsyncIOScheduler()


async def radarr_import_job() -> None:
    async with AsyncSessionLocal() as session:
        await import_radarr_movies(session)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    """Startup/shutdown lifecycle with APScheduler."""
    try:
        scheduler.add_job(import_radarr_movies, "cron", hour=3, minute=0)
        scheduler.start()
        logger.info("✅ Scheduler started (daily import at 03:00)")
    except Exception as e:
        logger.exception("Failed to start scheduler: %s", e)

    yield  # ----> приложение работает

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
    app.include_router(radarr.router, prefix="/api/radarr")

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
