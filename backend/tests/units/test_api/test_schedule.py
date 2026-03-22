"""Unit tests for /api/v1/settings/schedules endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import SchedulePreset, ServiceType, SyncJobType
from app.services.schedule_constants import DEFAULT_PRESETS, DEFAULT_SCHEDULES
from tests.factories import SyncScheduleFactory


def _make_configs(service_types: list[ServiceType]) -> list:
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
) -> None:
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
) -> None:
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


@pytest.mark.asyncio
async def test_list_schedules_empty_db_uses_default_presets(
    async_client, mock_session, override_scheduler_dependency
) -> None:
    """Empty DB → response uses default presets from DEFAULT_PRESETS."""
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

    data = response.json()
    preset_map = {s["job_type"]: s["preset"] for s in data["schedules"]}
    for job_type in SyncJobType:
        assert preset_map[job_type.value] == DEFAULT_PRESETS[job_type].value


@pytest.mark.asyncio
async def test_list_schedules_is_enabled_true_when_service_configured(
    async_client, mock_session, override_scheduler_dependency
) -> None:
    """When RADARR service is configured → radarr_import job is_enabled=True."""
    with (
        patch(
            "app.api.schedule.schedule_repo.get_all_schedules",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.api.schedule.config_repo.get_all_configs",
            new_callable=AsyncMock,
            return_value=_make_configs([ServiceType.RADARR]),
        ),
    ):
        response = await async_client.get("/api/v1/settings/schedules")

    data = response.json()
    schedules_by_type = {s["job_type"]: s for s in data["schedules"]}
    assert schedules_by_type["radarr_import"]["is_enabled"] is True


@pytest.mark.asyncio
async def test_list_schedules_is_enabled_false_when_service_not_configured(
    async_client, mock_session, override_scheduler_dependency
) -> None:
    """When no services are configured → all jobs have is_enabled=False."""
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

    data = response.json()
    for schedule in data["schedules"]:
        assert schedule["is_enabled"] is False


@pytest.mark.asyncio
async def test_list_schedules_is_running_reflects_db_value(
    async_client, mock_session, override_scheduler_dependency
) -> None:
    """When DB has is_running=True for a job → response reflects that."""
    running_schedule = SyncScheduleFactory.build(
        job_type=SyncJobType.RADARR_IMPORT, is_running=True
    )
    other_schedules = [
        SyncScheduleFactory.build(job_type=jt)
        for jt in SyncJobType
        if jt != SyncJobType.RADARR_IMPORT
    ]

    with (
        patch(
            "app.api.schedule.schedule_repo.get_all_schedules",
            new_callable=AsyncMock,
            return_value=[running_schedule, *other_schedules],
        ),
        patch(
            "app.api.schedule.config_repo.get_all_configs",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        response = await async_client.get("/api/v1/settings/schedules")

    data = response.json()
    schedules_by_type = {s["job_type"]: s for s in data["schedules"]}
    assert schedules_by_type["radarr_import"]["is_running"] is True


@pytest.mark.asyncio
async def test_list_schedules_next_run_at_from_scheduler(
    async_client, mock_session, override_scheduler_dependency, mock_scheduler
) -> None:
    """next_run_at is populated from APScheduler job.next_run_time."""
    fixed_time = datetime(2026, 3, 22, 22, 10, tzinfo=UTC)
    mock_job = MagicMock()
    mock_job.next_run_time = fixed_time
    mock_scheduler.get_job.return_value = mock_job

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

    data = response.json()
    # All schedules should have next_run_at from the mock
    for schedule in data["schedules"]:
        assert schedule["next_run_at"] is not None


@pytest.mark.asyncio
async def test_list_schedules_next_run_at_none_when_job_not_found(
    async_client, mock_session, override_scheduler_dependency, mock_scheduler
) -> None:
    """When scheduler.get_job returns None → next_run_at is null."""
    mock_scheduler.get_job.return_value = None

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

    data = response.json()
    for schedule in data["schedules"]:
        assert schedule["next_run_at"] is None


@pytest.mark.asyncio
async def test_list_schedules_response_has_all_required_fields(
    async_client, mock_session, override_scheduler_dependency
) -> None:
    """Every schedule item contains all required response fields."""
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

    data = response.json()
    required_fields = {
        "job_type",
        "preset",
        "cron_expression",
        "is_enabled",
        "is_running",
        "last_run_at",
        "next_run_at",
    }
    for schedule in data["schedules"]:
        assert required_fields.issubset(set(schedule.keys()))


@pytest.mark.asyncio
async def test_list_schedules_contains_all_job_types(
    async_client, mock_session, override_scheduler_dependency
) -> None:
    """Response contains all 7 known job types."""
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

    data = response.json()
    returned_types = {s["job_type"] for s in data["schedules"]}
    expected_types = {jt.value for jt in SyncJobType}
    assert returned_types == expected_types


# ---------------------------------------------------------------------------
# PUT /api/v1/settings/schedules/{job_type}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_schedule_daily(
    async_client, mock_session, override_scheduler_dependency, mock_scheduler
) -> None:
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
) -> None:
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
) -> None:
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
) -> None:
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
) -> None:
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
) -> None:
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
) -> None:
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


@pytest.mark.asyncio
async def test_update_schedule_invalid_job_type_returns_422(
    async_client, mock_session, override_scheduler_dependency
) -> None:
    """Unknown job_type path param → 422."""
    response = await async_client.put(
        "/api/v1/settings/schedules/nonexistent_job",
        json={"preset": "daily"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_schedule_reschedule_failure_returns_500(
    async_client, mock_session, override_scheduler_dependency, mock_scheduler
) -> None:
    """When scheduler.reschedule_job raises → 500."""
    job_type = SyncJobType.RADARR_IMPORT
    schedule = SyncScheduleFactory.build(
        job_type=job_type, preset=SchedulePreset.DAILY, cron_expression="10 1 * * *"
    )
    mock_scheduler.reschedule_job.side_effect = RuntimeError("Scheduler error")

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

    assert response.status_code == 500


@pytest.mark.asyncio
async def test_update_schedule_daily_uses_default_minute_and_hour(
    async_client, mock_session, override_scheduler_dependency, mock_scheduler
) -> None:
    """Daily preset builds cron from DEFAULT_SCHEDULES minute+hour for that job."""
    job_type = SyncJobType.RADARR_IMPORT
    default_cron = DEFAULT_SCHEDULES[job_type]
    default_parts = default_cron.split()
    expected_minute = default_parts[0]
    expected_hour = default_parts[1]

    schedule = SyncScheduleFactory.build(
        job_type=job_type,
        preset=SchedulePreset.DAILY,
        cron_expression=f"{expected_minute} {expected_hour} * * *",
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
    # Scheduler was called with the default minute/hour
    mock_scheduler.reschedule_job.assert_called_once_with(
        job_type.value,
        trigger="cron",
        minute=expected_minute,
        hour=expected_hour,
        day="*",
        month="*",
        day_of_week="*",
    )


@pytest.mark.asyncio
async def test_update_schedule_weekly_uses_day_of_week_0(
    async_client, mock_session, override_scheduler_dependency, mock_scheduler
) -> None:
    """Weekly preset always uses day_of_week=0 (Sunday)."""
    job_type = SyncJobType.JELLYFIN_USERS_IMPORT
    default_cron = DEFAULT_SCHEDULES[job_type]
    default_parts = default_cron.split()
    minute, hour = default_parts[0], default_parts[1]

    schedule = SyncScheduleFactory.build(
        job_type=job_type,
        preset=SchedulePreset.WEEKLY,
        cron_expression=f"{minute} {hour} * * 0",
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
    call_kwargs = mock_scheduler.reschedule_job.call_args
    assert call_kwargs.kwargs["day_of_week"] == "0"
    assert call_kwargs.kwargs["day"] == "*"


@pytest.mark.asyncio
async def test_update_schedule_monthly_uses_day_1(
    async_client, mock_session, override_scheduler_dependency, mock_scheduler
) -> None:
    """Monthly preset always uses day=1."""
    job_type = SyncJobType.JELLYFIN_SERIES_IMPORT
    default_cron = DEFAULT_SCHEDULES[job_type]
    default_parts = default_cron.split()
    minute, hour = default_parts[0], default_parts[1]

    schedule = SyncScheduleFactory.build(
        job_type=job_type,
        preset=SchedulePreset.MONTHLY,
        cron_expression=f"{minute} {hour} 1 * *",
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
    call_kwargs = mock_scheduler.reschedule_job.call_args
    assert call_kwargs.kwargs["day"] == "1"
    assert call_kwargs.kwargs["day_of_week"] == "*"


@pytest.mark.asyncio
async def test_update_schedule_custom_cron_expression_stored_as_is(
    async_client, mock_session, override_scheduler_dependency, mock_scheduler
) -> None:
    """For custom preset the user's cron expression is passed to reschedule unchanged."""
    job_type = SyncJobType.SONARR_IMPORT
    custom_expr = "5 4 * * 2"
    schedule = SyncScheduleFactory.build(
        job_type=job_type, preset=SchedulePreset.CUSTOM, cron_expression=custom_expr
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
            json={"preset": "custom", "cron_expression": custom_expr},
        )

    assert response.status_code == 200
    mock_scheduler.reschedule_job.assert_called_once_with(
        job_type.value,
        trigger="cron",
        minute="5",
        hour="4",
        day="*",
        month="*",
        day_of_week="2",
    )


@pytest.mark.asyncio
async def test_update_schedule_non_custom_ignores_provided_cron_expression(
    async_client, mock_session, override_scheduler_dependency, mock_scheduler
) -> None:
    """For daily preset, even if cron_expression is provided it is ignored."""
    job_type = SyncJobType.RADARR_IMPORT
    default_cron = DEFAULT_SCHEDULES[job_type]
    default_parts = default_cron.split()
    minute, hour = default_parts[0], default_parts[1]

    schedule = SyncScheduleFactory.build(
        job_type=job_type,
        preset=SchedulePreset.DAILY,
        cron_expression=f"{minute} {hour} * * *",
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
        # Deliberately pass a cron_expression that would conflict if used
        response = await async_client.put(
            f"/api/v1/settings/schedules/{job_type.value}",
            json={"preset": "daily", "cron_expression": "0 99 * * *"},
        )

    assert response.status_code == 200
    # The schedule should use default minute/hour, not "0 99"
    call_kwargs = mock_scheduler.reschedule_job.call_args.kwargs
    assert call_kwargs["minute"] == minute
    assert call_kwargs["hour"] == hour


@pytest.mark.asyncio
async def test_update_schedule_custom_conflict_with_default_job_not_in_db(
    async_client, mock_session, override_scheduler_dependency
) -> None:
    """Custom cron conflicting with a default schedule for job not yet in DB → 409."""
    job_type = SyncJobType.RADARR_IMPORT
    # Radarr default is "10 1 * * *" in schedule_constants — use sonarr's default to conflict
    sonarr_default = DEFAULT_SCHEDULES[SyncJobType.SONARR_IMPORT]

    # DB is empty — no saved schedules at all
    with patch(
        "app.api.schedule.schedule_repo.get_all_schedules",
        new_callable=AsyncMock,
        return_value=[],
    ):
        response = await async_client.put(
            f"/api/v1/settings/schedules/{job_type.value}",
            json={"preset": "custom", "cron_expression": sonarr_default},
        )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_update_schedule_response_has_correct_job_type(
    async_client, mock_session, override_scheduler_dependency, mock_scheduler
) -> None:
    """Response job_type matches the path param."""
    job_type = SyncJobType.JELLYFIN_MOVIES_IMPORT
    schedule = SyncScheduleFactory.build(
        job_type=job_type,
        preset=SchedulePreset.DAILY,
        cron_expression="20 1 * * *",
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
    assert response.json()["job_type"] == job_type.value


@pytest.mark.asyncio
async def test_update_schedule_cron_expression_too_long_returns_422(
    async_client, mock_session, override_scheduler_dependency
) -> None:
    """cron_expression exceeding max_length=100 → 422."""
    job_type = SyncJobType.RADARR_IMPORT
    long_expr = "0 " + "1" * 101

    response = await async_client.put(
        f"/api/v1/settings/schedules/{job_type.value}",
        json={"preset": "custom", "cron_expression": long_expr},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_schedule_missing_preset_returns_422(
    async_client, mock_session, override_scheduler_dependency
) -> None:
    """Missing preset field → 422."""
    job_type = SyncJobType.RADARR_IMPORT

    response = await async_client.put(
        f"/api/v1/settings/schedules/{job_type.value}",
        json={},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_schedule_invalid_preset_value_returns_422(
    async_client, mock_session, override_scheduler_dependency
) -> None:
    """Invalid preset value → 422."""
    job_type = SyncJobType.RADARR_IMPORT

    response = await async_client.put(
        f"/api/v1/settings/schedules/{job_type.value}",
        json={"preset": "every_hour"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_schedule_is_enabled_in_response_uses_service_config(
    async_client, mock_session, override_scheduler_dependency, mock_scheduler
) -> None:
    """After update, is_enabled in response reflects current service config state."""
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
            return_value=_make_configs([ServiceType.RADARR]),
        ),
    ):
        response = await async_client.put(
            f"/api/v1/settings/schedules/{job_type.value}",
            json={"preset": "daily"},
        )

    assert response.status_code == 200
    assert response.json()["is_enabled"] is True
