"""API endpoints for manual sync job triggering."""

import asyncio

from fastapi import Depends, HTTPException
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import SyncJobType
from app.schemas.sync_schedule import SyncTriggerResponse
from app.services import schedule_repository as schedule_repo
from app.services import service_config_repository as config_repo
from app.services.schedule_constants import JOB_REGISTRY

router = APIRouter(prefix="/api/v1/sync", tags=["Sync"])


@router.post("/trigger/{job_type}", status_code=202, response_model=SyncTriggerResponse)
async def trigger_sync_job(
    job_type: SyncJobType,
    session: AsyncSession = Depends(get_session),
) -> SyncTriggerResponse:
    required_service = JOB_REGISTRY[job_type][1]

    config = await config_repo.get_config_by_service(session, required_service)
    if config is None:
        raise HTTPException(status_code=422, detail="Service not configured")

    schedule = await schedule_repo.get_schedule_by_job(session, job_type)
    if schedule and schedule.is_running:
        raise HTTPException(status_code=409, detail="Job is already running")

    job_func = JOB_REGISTRY[job_type][0]
    asyncio.create_task(job_func())  # noqa: RUF006

    return SyncTriggerResponse(job_type=job_type, message="Sync job started")
