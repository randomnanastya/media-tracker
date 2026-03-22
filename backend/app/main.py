import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, jellyfin, radarr, schedule, settings, sonarr
from app.config import logger
from app.database import AsyncSessionLocal
from app.dependencies.auth import get_current_user
from app.exceptions.handlers import register_exception_handlers
from app.models import SyncJobType
from app.services import schedule_repository as schedule_repo
from app.services.schedule_constants import DEFAULT_SCHEDULES, JOB_REGISTRY
from app.utils.cron_utils import parse_cron_to_apscheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    """Startup/shutdown lifecycle with APScheduler."""
    scheduler = AsyncIOScheduler()
    try:
        app_env = os.getenv("APP_ENV", "development")
        jwt_secret = os.getenv("JWT_SECRET", "")
        if app_env == "production" and not jwt_secret:
            raise RuntimeError("JWT_SECRET is required in production")

        async with AsyncSessionLocal() as session:
            db_schedules = await schedule_repo.get_all_schedules(session)
            for s in db_schedules:
                if s.is_running:
                    await schedule_repo.set_running_status(session, s.job_type, False)
            await session.commit()

        if db_schedules:
            schedules_map = {s.job_type: s.cron_expression for s in db_schedules}
        else:
            schedules_map = {job_type: DEFAULT_SCHEDULES[job_type] for job_type in SyncJobType}

        for job_type, (func, _) in JOB_REGISTRY.items():
            cron_expr = schedules_map.get(job_type, DEFAULT_SCHEDULES[job_type])
            cron_kwargs = parse_cron_to_apscheduler(cron_expr)
            scheduler.add_job(
                func,
                "cron",
                id=job_type.value,
                misfire_grace_time=300,
                coalesce=True,
                max_instances=1,
                **cron_kwargs,
            )
            logger.info("Scheduled %s: %s", job_type.value, cron_expr)

        app.state.scheduler = scheduler
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


def _get_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Media Tracker API",
        description="Collects and stores stats from Sonarr, Radarr, and Jellyfin",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(auth.router)
    app.include_router(radarr.router, dependencies=[Depends(get_current_user)])
    app.include_router(sonarr.router, dependencies=[Depends(get_current_user)])
    app.include_router(jellyfin.router, dependencies=[Depends(get_current_user)])
    app.include_router(settings.router, dependencies=[Depends(get_current_user)])
    app.include_router(schedule.router, dependencies=[Depends(get_current_user)])

    # Register exception handlers
    register_exception_handlers(app)

    return app


# Create app instance
app: FastAPI = create_app()


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Media Tracker API is running"}


@app.get("/health", include_in_schema=False)
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
