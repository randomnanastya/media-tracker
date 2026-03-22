"""API endpoints for sync schedule management."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, HTTPException
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.scheduler import get_scheduler
from app.models import SchedulePreset, SyncJobType
from app.schemas.sync_schedule import (
    SyncScheduleListResponse,
    SyncScheduleRequest,
    SyncScheduleResponse,
)
from app.services import schedule_repository as schedule_repo
from app.services import service_config_repository as config_repo
from app.services.schedule_constants import DEFAULT_PRESETS, DEFAULT_SCHEDULES, JOB_REGISTRY
from app.utils.cron_utils import check_conflicts, parse_cron_to_apscheduler, validate_cron

router = APIRouter(prefix="/api/v1/settings/schedules", tags=["Settings"])


@router.get("", response_model=SyncScheduleListResponse)
async def list_schedules(
    session: AsyncSession = Depends(get_session),
    scheduler: AsyncIOScheduler = Depends(get_scheduler),
) -> SyncScheduleListResponse:
    db_schedules = await schedule_repo.get_all_schedules(session)
    all_configs = await config_repo.get_all_configs(session)
    configured_services = {c.service_type for c in all_configs}

    schedules_map = {s.job_type: s for s in db_schedules}

    result = []
    for job_type in SyncJobType:
        db_schedule = schedules_map.get(job_type)
        cron_expr = db_schedule.cron_expression if db_schedule else DEFAULT_SCHEDULES[job_type]
        preset = db_schedule.preset if db_schedule else DEFAULT_PRESETS[job_type]
        is_running = db_schedule.is_running if db_schedule else False
        last_run_at = db_schedule.last_run_at if db_schedule else None

        required_service = JOB_REGISTRY[job_type][1]
        is_enabled = required_service in configured_services

        job = scheduler.get_job(job_type.value)
        next_run_at = job.next_run_time if job else None

        result.append(
            SyncScheduleResponse(
                job_type=job_type,
                preset=preset,
                cron_expression=cron_expr,
                is_enabled=is_enabled,
                is_running=is_running,
                last_run_at=last_run_at,
                next_run_at=next_run_at,
            )
        )

    return SyncScheduleListResponse(schedules=result)


@router.put("/{job_type}", response_model=SyncScheduleResponse)
async def update_schedule(
    job_type: SyncJobType,
    body: SyncScheduleRequest,
    session: AsyncSession = Depends(get_session),
    scheduler: AsyncIOScheduler = Depends(get_scheduler),
) -> SyncScheduleResponse:
    if body.preset == SchedulePreset.CUSTOM:
        if body.cron_expression is None:
            raise HTTPException(
                status_code=422, detail="cron_expression is required for custom preset"
            )
        if not validate_cron(body.cron_expression):
            raise HTTPException(status_code=400, detail="Invalid cron expression")
        all_schedules = await schedule_repo.get_all_schedules(session)
        other_exprs = [
            s.cron_expression if s.job_type != job_type else DEFAULT_SCHEDULES[s.job_type]
            for s in all_schedules
            if s.job_type != job_type
        ]
        # Also include defaults for jobs not yet in DB
        db_job_types = {s.job_type for s in all_schedules}
        for jt in SyncJobType:
            if jt != job_type and jt not in db_job_types:
                other_exprs.append(DEFAULT_SCHEDULES[jt])
        if check_conflicts(body.cron_expression, other_exprs):
            raise HTTPException(status_code=409, detail="Schedule conflicts with another job")
        cron_expr = body.cron_expression
    else:
        default_cron = DEFAULT_SCHEDULES[job_type]
        parts = default_cron.split()
        minute, hour = parts[0], parts[1]
        if body.preset == SchedulePreset.DAILY:
            cron_expr = f"{minute} {hour} * * *"
        elif body.preset == SchedulePreset.WEEKLY:
            cron_expr = f"{minute} {hour} * * 0"
        else:  # MONTHLY
            cron_expr = f"{minute} {hour} 1 * *"

    schedule = await schedule_repo.upsert_schedule(session, job_type, body.preset, cron_expr)

    try:
        scheduler.reschedule_job(
            job_type.value, trigger="cron", **parse_cron_to_apscheduler(cron_expr)
        )
    except Exception as err:
        raise HTTPException(status_code=500, detail="Failed to reschedule job") from err

    try:
        await session.commit()
    except Exception as err:
        await session.rollback()
        raise HTTPException(status_code=500, detail="Failed to save schedule") from err

    all_configs = await config_repo.get_all_configs(session)
    configured_services = {c.service_type for c in all_configs}
    required_service = JOB_REGISTRY[job_type][1]
    is_enabled = required_service in configured_services

    job = scheduler.get_job(job_type.value)
    next_run_at = job.next_run_time if job else None

    return SyncScheduleResponse(
        job_type=job_type,
        preset=schedule.preset,
        cron_expression=schedule.cron_expression,
        is_enabled=is_enabled,
        is_running=schedule.is_running,
        last_run_at=schedule.last_run_at,
        next_run_at=next_run_at,
    )
