import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.api import radarr
from app.services.radarr_service import import_radarr_movies
from app.database import get_session  # <- импортируем рабочий get_session

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(import_radarr_movies, "cron", hour=3, minute=0)
    # --- startup ---
    scheduler.start()
    print("✅ Scheduler started")
    yield
    # --- shutdown ---
    scheduler.shutdown(wait=False)
    print("🛑 Scheduler stopped")


app = FastAPI(title="Media Tracker", lifespan=lifespan)

# Radarr API v1
app.include_router(radarr.router, prefix="/api/v1/radarr")


@app.get("/health")
def health_check():
    return {"status": "ok"}
