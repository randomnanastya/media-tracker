from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Request


def get_scheduler(request: Request) -> AsyncIOScheduler:
    return request.app.state.scheduler
