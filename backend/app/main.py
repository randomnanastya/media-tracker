import logging

from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.api import radarr
from app.services.radarr_service import import_radarr_movies

logger = logging.getLogger(__name__)

app = FastAPI(title="Media Tracker")

# Radarr API v1
app.include_router(radarr.router, prefix="/api/v1/radarr")

# Scheduler
scheduler = AsyncIOScheduler()
scheduler.add_job(import_radarr_movies, "cron", hour=3, minute=0)
scheduler.start()

@app.get("/health")
def health_check():
    return {"status": "ok"}
