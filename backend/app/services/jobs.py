from collections.abc import Awaitable, Callable, Coroutine
from datetime import UTC, datetime
from functools import wraps
from typing import Any

from app.config import logger
from app.database import AsyncSessionLocal
from app.models import ServiceType, SyncJobType
from app.services import schedule_repository as schedule_repo
from app.services.import_jellyfin_movies_service import import_jellyfin_movies
from app.services.import_jellyfin_series_service import import_jellyfin_series
from app.services.jellyfin_users_service import import_jellyfin_users
from app.services.radarr_service import import_radarr_movies
from app.services.service_config_repository import get_config_by_service
from app.services.sonarr_service import import_sonarr_series
from app.services.sync_jellyfin_watched_movies_service import sync_jellyfin_watched_movies
from app.services.sync_jellyfin_watched_series_service import sync_jellyfin_watched_series

_JOB_FUNC_TO_TYPE: dict[str, SyncJobType] = {}


def log_job_execution(
    job_func: Callable[..., Awaitable[None]],
) -> Callable[..., Coroutine[Any, Any, None]]:
    @wraps(job_func)
    async def wrapper(*args: Any, **kwargs: Any) -> None:
        job_name = job_func.__name__
        job_type = _JOB_FUNC_TO_TYPE.get(job_name)
        start_time = datetime.now(UTC)
        logger.info("🚀 %s started at %s", job_name, start_time)

        if job_type is not None:
            async with AsyncSessionLocal() as session:
                await schedule_repo.set_running_status(session, job_type, True)
                await session.commit()

        try:
            await job_func(*args, **kwargs)
            end_time = datetime.now(UTC)
            logger.info("✅ %s completed at %s", job_name, end_time)
            logger.info("⏱ %s took %s seconds", job_name, (end_time - start_time).total_seconds())
        except Exception as e:
            logger.exception("❌ %s failed: %s", job_name, str(e))
            raise
        finally:
            if job_type is not None:
                async with AsyncSessionLocal() as session:
                    await schedule_repo.set_running_status(session, job_type, False)
                    await schedule_repo.update_last_run(session, job_type)
                    await session.commit()

    return wrapper


@log_job_execution
async def _run_radarr_import() -> None:
    async with AsyncSessionLocal() as session:
        await import_radarr_movies(session)


@log_job_execution
async def _run_sonarr_import() -> None:
    async with AsyncSessionLocal() as session:
        await import_sonarr_series(session)


@log_job_execution
async def _run_jellyfin_import_users() -> None:
    async with AsyncSessionLocal() as session:
        await import_jellyfin_users(session)


@log_job_execution
async def _run_jellyfin_import_movies() -> None:
    async with AsyncSessionLocal() as session:
        await import_jellyfin_movies(session)


@log_job_execution
async def _run_jellyfin_import_series() -> None:
    async with AsyncSessionLocal() as session:
        await import_jellyfin_series(session)


@log_job_execution
async def _run_jellyfin_sync_movie_watch_history() -> None:
    async with AsyncSessionLocal() as session:
        await sync_jellyfin_watched_movies(session)


@log_job_execution
async def _run_jellyfin_sync_series_watch_history() -> None:
    async with AsyncSessionLocal() as session:
        await sync_jellyfin_watched_series(session)


_JOB_FUNC_TO_TYPE.update(
    {
        _run_jellyfin_import_users.__name__: SyncJobType.JELLYFIN_USERS_IMPORT,
        _run_radarr_import.__name__: SyncJobType.RADARR_IMPORT,
        _run_jellyfin_import_movies.__name__: SyncJobType.JELLYFIN_MOVIES_IMPORT,
        _run_jellyfin_sync_movie_watch_history.__name__: SyncJobType.JELLYFIN_MOVIE_WATCH_HISTORY,
        _run_sonarr_import.__name__: SyncJobType.SONARR_IMPORT,
        _run_jellyfin_import_series.__name__: SyncJobType.JELLYFIN_SERIES_IMPORT,
        _run_jellyfin_sync_series_watch_history.__name__: SyncJobType.JELLYFIN_SERIES_WATCH_HISTORY,
    }
)


async def radarr_import_job() -> None:
    async with AsyncSessionLocal() as session:
        config = await get_config_by_service(session, ServiceType.RADARR)
    if not config:
        logger.info("Skipping radarr_import: service not configured")
        return
    await _run_radarr_import()


async def sonarr_import_job() -> None:
    async with AsyncSessionLocal() as session:
        config = await get_config_by_service(session, ServiceType.SONARR)
    if not config:
        logger.info("Skipping sonarr_import: service not configured")
        return
    await _run_sonarr_import()


async def jellyfin_import_users_job() -> None:
    async with AsyncSessionLocal() as session:
        config = await get_config_by_service(session, ServiceType.JELLYFIN)
    if not config:
        logger.info("Skipping jellyfin_import_users: service not configured")
        return
    await _run_jellyfin_import_users()


async def jellyfin_import_movies_job() -> None:
    async with AsyncSessionLocal() as session:
        config = await get_config_by_service(session, ServiceType.JELLYFIN)
    if not config:
        logger.info("Skipping jellyfin_import_movies: service not configured")
        return
    await _run_jellyfin_import_movies()


async def jellyfin_import_series_job() -> None:
    async with AsyncSessionLocal() as session:
        config = await get_config_by_service(session, ServiceType.JELLYFIN)
    if not config:
        logger.info("Skipping jellyfin_import_series: service not configured")
        return
    await _run_jellyfin_import_series()


async def jellyfin_sync_movie_watch_history_job() -> None:
    async with AsyncSessionLocal() as session:
        config = await get_config_by_service(session, ServiceType.JELLYFIN)
    if not config:
        logger.info("Skipping jellyfin_sync_movie_watch_history: service not configured")
        return
    await _run_jellyfin_sync_movie_watch_history()


async def jellyfin_sync_series_watch_history_job() -> None:
    async with AsyncSessionLocal() as session:
        config = await get_config_by_service(session, ServiceType.JELLYFIN)
    if not config:
        logger.info("Skipping jellyfin_sync_series_watch_history: service not configured")
        return
    await _run_jellyfin_sync_series_watch_history()
