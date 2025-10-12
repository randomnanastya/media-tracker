from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from app.api import radarr
from app.core.logging import logger
from app.database import AsyncSessionLocal  # <- импортируем рабочий get_session
from app.services.radarr_service import import_radarr_movies

scheduler = AsyncIOScheduler()


async def radarr_import_job():
    async with AsyncSessionLocal() as session:
        await import_radarr_movies(session)


@asynccontextmanager
async def lifespan(app: FastAPI):
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


app = FastAPI(title="Media Tracker", lifespan=lifespan)

# Radarr API v1
app.include_router(radarr.router, prefix="/api/v1/radarr")


@app.get("/health")
def health_check():
    return {"status": "ok"}
