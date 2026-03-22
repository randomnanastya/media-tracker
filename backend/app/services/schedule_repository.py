"""Repository for SyncSchedule CRUD operations."""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SchedulePreset, SyncJobType, SyncSchedule


async def get_all_schedules(session: AsyncSession) -> list[SyncSchedule]:
    result = await session.execute(select(SyncSchedule))
    return list(result.scalars().all())


async def get_schedule_by_job(session: AsyncSession, job_type: SyncJobType) -> SyncSchedule | None:
    result = await session.execute(select(SyncSchedule).where(SyncSchedule.job_type == job_type))
    return result.scalars().first()


async def upsert_schedule(
    session: AsyncSession,
    job_type: SyncJobType,
    preset: SchedulePreset,
    cron_expression: str,
) -> SyncSchedule:
    schedule = await get_schedule_by_job(session, job_type)
    if schedule is None:
        schedule = SyncSchedule(
            job_type=job_type,
            preset=preset,
            cron_expression=cron_expression,
        )
        session.add(schedule)
    else:
        schedule.preset = preset
        schedule.cron_expression = cron_expression
    return schedule


async def set_running_status(
    session: AsyncSession, job_type: SyncJobType, is_running: bool
) -> None:
    await session.execute(
        update(SyncSchedule).where(SyncSchedule.job_type == job_type).values(is_running=is_running)
    )


async def update_last_run(session: AsyncSession, job_type: SyncJobType) -> None:
    await session.execute(
        update(SyncSchedule)
        .where(SyncSchedule.job_type == job_type)
        .values(last_run_at=datetime.now(UTC))
    )
