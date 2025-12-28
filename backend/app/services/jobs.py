from collections.abc import Awaitable, Callable, Coroutine
from datetime import UTC, datetime
from functools import wraps
from typing import Any

from app.config import logger
from app.database import AsyncSessionLocal
from app.services.jellyfin_users_service import import_jellyfin_users
from app.services.radarr_service import import_radarr_movies
from app.services.sonarr_service import import_sonarr_series
from app.services.sync_jellyfin_movies_service import sync_jellyfin_movies


def log_job_execution(
    job_func: Callable[..., Awaitable[None]],
) -> Callable[..., Coroutine[Any, Any, None]]:
    @wraps(job_func)
    async def wrapper(*args: Any, **kwargs: Any) -> None:
        job_name = job_func.__name__
        start_time = datetime.now(UTC)
        logger.info("🚀 %s started at %s", job_name, start_time)
        try:
            await job_func(*args, **kwargs)  # No need to capture result
            end_time = datetime.now(UTC)
            logger.info("✅ %s completed at %s", job_name, end_time)
            logger.info("⏱ %s took %s seconds", job_name, (end_time - start_time).total_seconds())
        except Exception as e:
            logger.exception("❌ %s failed: %s", job_name, str(e))
            raise

    return wrapper


@log_job_execution
async def radarr_import_job() -> None:
    async with AsyncSessionLocal() as session:
        logger.debug("Processing Radarr data...")
        await import_radarr_movies(session)


@log_job_execution
async def sonarr_import_job() -> None:
    async with AsyncSessionLocal() as session:
        logger.debug("Processing Sonarr data...")
        await import_sonarr_series(session)


@log_job_execution
async def jellyfin_import_users_job() -> None:
    async with AsyncSessionLocal() as session:
        logger.debug("Processing Jellyfin Users data...")
        await import_jellyfin_users(session)


@log_job_execution
async def jellyfin_sync_movies_job() -> None:
    async with AsyncSessionLocal() as session:
        logger.debug("Processing Jellyfin sync movies data...")
        await sync_jellyfin_movies(session)
