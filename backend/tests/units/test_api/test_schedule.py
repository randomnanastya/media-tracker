"""Unit tests for /api/v1/settings/schedules endpoints."""

from unittest.mock import AsyncMock, patch

import pytest

from app.models import SchedulePreset, ServiceType, SyncJobType
from app.services.schedule_constants import DEFAULT_SCHEDULES
from tests.factories import SyncScheduleFactory


def _make_configs(service_types: list[ServiceType]) -> list:
    from unittest.mock import MagicMock

    from app.models import ServiceConfig

    configs = []
    for st in service_types:
        cfg = MagicMock(spec=ServiceConfig)
        cfg.service_type = st
        configs.append(cfg)
    return configs


# ---------------------------------------------------------------------------
# GET /api/v1/settings/schedules
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_schedules_with_db_schedules(
    async_client, mock_session, override_scheduler_dependency
):
    """7 schedules from DB → 200 with 7 items."""
    schedules = [SyncScheduleFactory.build(job_type=job_type) for job_type in SyncJobType]

    with (
        patch(
            "app.api.schedule.schedule_repo.get_all_schedules",
            new_callable=AsyncMock,
            return_value=schedules,
        ),
        patch(
            "app.api.schedule.config_repo.get_all_configs",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        response = await async_client.get("/api/v1/settings/schedules")

    assert response.status_code == 200
    data = response.json()
    assert len(data["schedules"]) == 7


@pytest.mark.asyncio
async def test_list_schedules_empty_db_uses_defaults(
    async_client, mock_session, override_scheduler_dependency
):
    """Empty DB → 200 with 7 items using default cron expressions."""
    with (
        patch(
            "app.api.schedule.schedule_repo.get_all_schedules",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.api.schedule.config_repo.get_all_configs",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        response = await async_client.get("/api/v1/settings/schedules")

    assert response.status_code == 200
    data = response.json()
    assert len(data["schedules"]) == 7
    cron_map = {s["job_type"]: s["cron_expression"] for s in data["schedules"]}
    for job_type in SyncJobType:
        assert cron_map[job_type.value] == DEFAULT_SCHEDULES[job_type]


# ---------------------------------------------------------------------------
# PUT /api/v1/settings/schedules/{job_type}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_schedule_daily(
    async_client, mock_session, override_scheduler_dependency, mock_scheduler
):
    """preset=daily → 200, cron_expression matches {min} {hour} * * *."""
    job_type = SyncJobType.RADARR_IMPORT
    schedule = SyncScheduleFactory.build(
        job_type=job_type, preset=SchedulePreset.DAILY, cron_expression="10 1 * * *"
    )

    with (
        patch(
            "app.api.schedule.schedule_repo.upsert_schedule",
            new_callable=AsyncMock,
            return_value=schedule,
        ),
        patch(
            "app.api.schedule.config_repo.get_all_configs",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        response = await async_client.put(
            f"/api/v1/settings/schedules/{job_type.value}",
            json={"preset": "daily"},
        )

    assert response.status_code == 200
    data = response.json()
    parts = data["cron_expression"].split()
    assert len(parts) == 5
    assert parts[2] == "*"
    assert parts[3] == "*"
    assert parts[4] == "*"


@pytest.mark.asyncio
async def test_update_schedule_weekly(
    async_client, mock_session, override_scheduler_dependency, mock_scheduler
):
    """preset=weekly → 200, cron_expression ends with * * 0."""
    job_type = SyncJobType.RADARR_IMPORT
    schedule = SyncScheduleFactory.build(
        job_type=job_type, preset=SchedulePreset.WEEKLY, cron_expression="10 1 * * 0"
    )

    with (
        patch(
            "app.api.schedule.schedule_repo.upsert_schedule",
            new_callable=AsyncMock,
            return_value=schedule,
        ),
        patch(
            "app.api.schedule.config_repo.get_all_configs",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        response = await async_client.put(
            f"/api/v1/settings/schedules/{job_type.value}",
            json={"preset": "weekly"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["cron_expression"].endswith("* * 0")
    mock_scheduler.reschedule_job.assert_called_once_with(
        job_type.value,
        trigger="cron",
        minute="10",
        hour="1",
        day="*",
        month="*",
        day_of_week="0",
    )


@pytest.mark.asyncio
async def test_update_schedule_monthly(
    async_client, mock_session, override_scheduler_dependency, mock_scheduler
):
    """preset=monthly → 200, cron_expression has format {min} {hour} 1 * *."""
    job_type = SyncJobType.RADARR_IMPORT
    schedule = SyncScheduleFactory.build(
        job_type=job_type, preset=SchedulePreset.MONTHLY, cron_expression="10 1 1 * *"
    )

    with (
        patch(
            "app.api.schedule.schedule_repo.upsert_schedule",
            new_callable=AsyncMock,
            return_value=schedule,
        ),
        patch(
            "app.api.schedule.config_repo.get_all_configs",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        response = await async_client.put(
            f"/api/v1/settings/schedules/{job_type.value}",
            json={"preset": "monthly"},
        )

    assert response.status_code == 200
    data = response.json()
    parts = data["cron_expression"].split()
    assert parts[2] == "1"
    assert parts[3] == "*"
    assert parts[4] == "*"
    mock_scheduler.reschedule_job.assert_called_once_with(
        job_type.value,
        trigger="cron",
        minute="10",
        hour="1",
        day="1",
        month="*",
        day_of_week="*",
    )


@pytest.mark.asyncio
async def test_update_schedule_custom_valid(
    async_client, mock_session, override_scheduler_dependency
):
    """preset=custom, valid cron, no conflicts → 200."""
    job_type = SyncJobType.RADARR_IMPORT
    schedule = SyncScheduleFactory.build(
        job_type=job_type, preset=SchedulePreset.CUSTOM, cron_expression="0 3 * * *"
    )

    with (
        patch(
            "app.api.schedule.schedule_repo.get_all_schedules",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.api.schedule.schedule_repo.upsert_schedule",
            new_callable=AsyncMock,
            return_value=schedule,
        ),
        patch(
            "app.api.schedule.config_repo.get_all_configs",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        response = await async_client.put(
            f"/api/v1/settings/schedules/{job_type.value}",
            json={"preset": "custom", "cron_expression": "0 3 * * *"},
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_schedule_custom_no_expression(
    async_client, mock_session, override_scheduler_dependency
):
    """preset=custom, cron_expression=None → 422."""
    job_type = SyncJobType.RADARR_IMPORT

    response = await async_client.put(
        f"/api/v1/settings/schedules/{job_type.value}",
        json={"preset": "custom"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_schedule_custom_invalid_cron(
    async_client, mock_session, override_scheduler_dependency
):
    """preset=custom, invalid cron → 400."""
    job_type = SyncJobType.RADARR_IMPORT

    response = await async_client.put(
        f"/api/v1/settings/schedules/{job_type.value}",
        json={"preset": "custom", "cron_expression": "not-a-cron"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_schedule_custom_conflicting_cron(
    async_client, mock_session, override_scheduler_dependency
):
    """preset=custom, conflicting cron → 409."""
    job_type = SyncJobType.RADARR_IMPORT
    # Another job with same cron
    other = SyncScheduleFactory.build(
        job_type=SyncJobType.SONARR_IMPORT,
        cron_expression="0 3 * * *",
    )

    with patch(
        "app.api.schedule.schedule_repo.get_all_schedules",
        new_callable=AsyncMock,
        return_value=[other],
    ):
        response = await async_client.put(
            f"/api/v1/settings/schedules/{job_type.value}",
            json={"preset": "custom", "cron_expression": "0 3 * * *"},
        )

    assert response.status_code == 409
