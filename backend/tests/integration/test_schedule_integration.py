"""Integration tests for /api/v1/settings/schedules with a real PostgreSQL DB."""

from unittest.mock import MagicMock

from sqlalchemy import select

from app.models import SchedulePreset, ServiceType, SyncJobType, SyncSchedule
from app.services.schedule_constants import DEFAULT_PRESETS, DEFAULT_SCHEDULES

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_schedule(
    session,
    job_type: SyncJobType = SyncJobType.RADARR_IMPORT,
    preset: SchedulePreset = SchedulePreset.DAILY,
    cron_expression: str = "10 1 * * *",
    is_running: bool = False,
) -> SyncSchedule:
    """Insert a SyncSchedule directly into the DB."""
    schedule = SyncSchedule(
        job_type=job_type,
        preset=preset,
        cron_expression=cron_expression,
        is_running=is_running,
    )
    session.add(schedule)
    await session.commit()
    await session.refresh(schedule)
    return schedule


def _mock_scheduler_with_no_jobs() -> MagicMock:
    mock = MagicMock()
    mock.get_job.return_value = None
    mock.reschedule_job = MagicMock()
    return mock


# ---------------------------------------------------------------------------
# GET /api/v1/settings/schedules — empty DB
# ---------------------------------------------------------------------------


async def test_list_schedules_empty_db_returns_defaults(client_with_db) -> None:
    """Empty DB → all 7 jobs returned with default cron expressions."""
    from app.dependencies.scheduler import get_scheduler
    from app.main import app

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        response = await client_with_db.get("/api/v1/settings/schedules")
    finally:
        app.dependency_overrides.pop(get_scheduler, None)

    assert response.status_code == 200
    data = response.json()
    assert len(data["schedules"]) == 7

    cron_map = {s["job_type"]: s["cron_expression"] for s in data["schedules"]}
    for job_type in SyncJobType:
        assert cron_map[job_type.value] == DEFAULT_SCHEDULES[job_type]


async def test_list_schedules_empty_db_default_presets(client_with_db) -> None:
    """Empty DB → all 7 jobs returned with correct default presets."""
    from app.dependencies.scheduler import get_scheduler
    from app.main import app

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        response = await client_with_db.get("/api/v1/settings/schedules")
    finally:
        app.dependency_overrides.pop(get_scheduler, None)

    data = response.json()
    preset_map = {s["job_type"]: s["preset"] for s in data["schedules"]}
    for job_type in SyncJobType:
        assert preset_map[job_type.value] == DEFAULT_PRESETS[job_type].value


async def test_list_schedules_all_disabled_when_no_service_configs(client_with_db) -> None:
    """Without any ServiceConfig rows → all jobs have is_enabled=False."""
    from app.dependencies.scheduler import get_scheduler
    from app.main import app

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        response = await client_with_db.get("/api/v1/settings/schedules")
    finally:
        app.dependency_overrides.pop(get_scheduler, None)

    data = response.json()
    for schedule in data["schedules"]:
        assert schedule["is_enabled"] is False


# ---------------------------------------------------------------------------
# GET — with data in DB
# ---------------------------------------------------------------------------


async def test_list_schedules_returns_saved_cron(client_with_db, session_for_test) -> None:
    """After saving a schedule to DB → GET returns the saved cron expression."""
    from app.dependencies.scheduler import get_scheduler
    from app.main import app

    await _create_schedule(
        session_for_test,
        job_type=SyncJobType.RADARR_IMPORT,
        preset=SchedulePreset.CUSTOM,
        cron_expression="5 4 * * 3",
    )

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        response = await client_with_db.get("/api/v1/settings/schedules")
    finally:
        app.dependency_overrides.pop(get_scheduler, None)

    data = response.json()
    schedules_by_type = {s["job_type"]: s for s in data["schedules"]}
    assert schedules_by_type["radarr_import"]["cron_expression"] == "5 4 * * 3"
    assert schedules_by_type["radarr_import"]["preset"] == "custom"


async def test_list_schedules_is_running_true_from_db(client_with_db, session_for_test) -> None:
    """When DB has is_running=True → GET reflects that."""
    from app.dependencies.scheduler import get_scheduler
    from app.main import app

    await _create_schedule(
        session_for_test,
        job_type=SyncJobType.SONARR_IMPORT,
        is_running=True,
    )

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        response = await client_with_db.get("/api/v1/settings/schedules")
    finally:
        app.dependency_overrides.pop(get_scheduler, None)

    data = response.json()
    schedules_by_type = {s["job_type"]: s for s in data["schedules"]}
    assert schedules_by_type["sonarr_import"]["is_running"] is True


async def test_list_schedules_mixed_db_and_defaults(client_with_db, session_for_test) -> None:
    """When only some jobs have DB records, others use defaults."""
    from app.dependencies.scheduler import get_scheduler
    from app.main import app

    await _create_schedule(
        session_for_test,
        job_type=SyncJobType.RADARR_IMPORT,
        preset=SchedulePreset.WEEKLY,
        cron_expression="10 1 * * 0",
    )

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        response = await client_with_db.get("/api/v1/settings/schedules")
    finally:
        app.dependency_overrides.pop(get_scheduler, None)

    data = response.json()
    schedules_by_type = {s["job_type"]: s for s in data["schedules"]}

    # Saved job uses saved values
    assert schedules_by_type["radarr_import"]["preset"] == "weekly"
    assert schedules_by_type["radarr_import"]["cron_expression"] == "10 1 * * 0"

    # Unsaved job uses defaults
    sonarr_default = DEFAULT_SCHEDULES[SyncJobType.SONARR_IMPORT]
    assert schedules_by_type["sonarr_import"]["cron_expression"] == sonarr_default


# ---------------------------------------------------------------------------
# PUT /api/v1/settings/schedules/{job_type}
# ---------------------------------------------------------------------------


async def test_put_daily_creates_new_schedule_row(client_with_db, session_for_test) -> None:
    """PUT daily → creates a new SyncSchedule row in the database."""
    from app.dependencies.scheduler import get_scheduler
    from app.main import app

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        response = await client_with_db.put(
            "/api/v1/settings/schedules/radarr_import",
            json={"preset": "daily"},
        )
    finally:
        app.dependency_overrides.pop(get_scheduler, None)

    assert response.status_code == 200

    result = await session_for_test.execute(
        select(SyncSchedule).where(SyncSchedule.job_type == SyncJobType.RADARR_IMPORT)
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.preset == SchedulePreset.DAILY


async def test_put_weekly_saves_correct_cron(client_with_db, session_for_test) -> None:
    """PUT weekly → cron in DB ends with '* * 0'."""
    from app.dependencies.scheduler import get_scheduler
    from app.main import app

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        response = await client_with_db.put(
            "/api/v1/settings/schedules/radarr_import",
            json={"preset": "weekly"},
        )
    finally:
        app.dependency_overrides.pop(get_scheduler, None)

    assert response.status_code == 200

    result = await session_for_test.execute(
        select(SyncSchedule).where(SyncSchedule.job_type == SyncJobType.RADARR_IMPORT)
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.cron_expression.endswith("* * 0")


async def test_put_monthly_saves_correct_cron(client_with_db, session_for_test) -> None:
    """PUT monthly → day field in saved cron is '1'."""
    from app.dependencies.scheduler import get_scheduler
    from app.main import app

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        response = await client_with_db.put(
            "/api/v1/settings/schedules/sonarr_import",
            json={"preset": "monthly"},
        )
    finally:
        app.dependency_overrides.pop(get_scheduler, None)

    assert response.status_code == 200

    result = await session_for_test.execute(
        select(SyncSchedule).where(SyncSchedule.job_type == SyncJobType.SONARR_IMPORT)
    )
    row = result.scalar_one_or_none()
    assert row is not None
    parts = row.cron_expression.split()
    assert parts[2] == "1"


async def test_put_custom_valid_saves_cron(client_with_db, session_for_test) -> None:
    """PUT custom with valid non-conflicting cron → saved in DB."""
    from app.dependencies.scheduler import get_scheduler
    from app.main import app

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        response = await client_with_db.put(
            "/api/v1/settings/schedules/radarr_import",
            json={"preset": "custom", "cron_expression": "5 4 * * 2"},
        )
    finally:
        app.dependency_overrides.pop(get_scheduler, None)

    assert response.status_code == 200

    result = await session_for_test.execute(
        select(SyncSchedule).where(SyncSchedule.job_type == SyncJobType.RADARR_IMPORT)
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.cron_expression == "5 4 * * 2"
    assert row.preset == SchedulePreset.CUSTOM


async def test_put_upsert_does_not_create_duplicates(client_with_db, session_for_test) -> None:
    """Multiple PUTs on the same job_type → only one row in DB."""
    from app.dependencies.scheduler import get_scheduler
    from app.main import app

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        for preset in ["daily", "weekly", "monthly"]:
            await client_with_db.put(
                "/api/v1/settings/schedules/radarr_import",
                json={"preset": preset},
            )
    finally:
        app.dependency_overrides.pop(get_scheduler, None)

    result = await session_for_test.execute(
        select(SyncSchedule).where(SyncSchedule.job_type == SyncJobType.RADARR_IMPORT)
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].preset == SchedulePreset.MONTHLY


async def test_put_updates_existing_schedule(client_with_db, session_for_test) -> None:
    """PUT on job that already has DB row → row is updated, not duplicated."""
    from app.dependencies.scheduler import get_scheduler
    from app.main import app

    await _create_schedule(
        session_for_test,
        job_type=SyncJobType.RADARR_IMPORT,
        preset=SchedulePreset.DAILY,
        cron_expression="10 1 * * *",
    )

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        response = await client_with_db.put(
            "/api/v1/settings/schedules/radarr_import",
            json={"preset": "weekly"},
        )
    finally:
        app.dependency_overrides.pop(get_scheduler, None)

    assert response.status_code == 200

    result = await session_for_test.execute(
        select(SyncSchedule).where(SyncSchedule.job_type == SyncJobType.RADARR_IMPORT)
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].preset == SchedulePreset.WEEKLY


async def test_put_custom_invalid_cron_returns_400_no_db_row(
    client_with_db, session_for_test
) -> None:
    """PUT custom with invalid cron → 400, no new DB row created."""
    from app.dependencies.scheduler import get_scheduler
    from app.main import app

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        response = await client_with_db.put(
            "/api/v1/settings/schedules/radarr_import",
            json={"preset": "custom", "cron_expression": "bad-cron"},
        )
    finally:
        app.dependency_overrides.pop(get_scheduler, None)

    assert response.status_code == 400

    result = await session_for_test.execute(
        select(SyncSchedule).where(SyncSchedule.job_type == SyncJobType.RADARR_IMPORT)
    )
    assert result.scalar_one_or_none() is None


async def test_put_custom_conflicting_with_existing_db_schedule_returns_409(
    client_with_db, session_for_test
) -> None:
    """Custom cron that conflicts with another saved schedule → 409."""
    from app.dependencies.scheduler import get_scheduler
    from app.main import app

    # Save sonarr with a specific cron
    await _create_schedule(
        session_for_test,
        job_type=SyncJobType.SONARR_IMPORT,
        preset=SchedulePreset.CUSTOM,
        cron_expression="0 3 * * *",
    )

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        # Try to set radarr to the same time
        response = await client_with_db.put(
            "/api/v1/settings/schedules/radarr_import",
            json={"preset": "custom", "cron_expression": "0 3 * * *"},
        )
    finally:
        app.dependency_overrides.pop(get_scheduler, None)

    assert response.status_code == 409


async def test_put_custom_no_expression_returns_422(client_with_db) -> None:
    """PUT custom without cron_expression → 422."""
    from app.dependencies.scheduler import get_scheduler
    from app.main import app

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        response = await client_with_db.put(
            "/api/v1/settings/schedules/radarr_import",
            json={"preset": "custom"},
        )
    finally:
        app.dependency_overrides.pop(get_scheduler, None)

    assert response.status_code == 422


async def test_put_calls_reschedule_job_on_scheduler(client_with_db, session_for_test) -> None:
    """PUT → scheduler.reschedule_job is called with correct args."""
    from app.dependencies.scheduler import get_scheduler
    from app.main import app

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        await client_with_db.put(
            "/api/v1/settings/schedules/radarr_import",
            json={"preset": "daily"},
        )
    finally:
        app.dependency_overrides.pop(get_scheduler, None)

    mock_scheduler.reschedule_job.assert_called_once()
    call_args = mock_scheduler.reschedule_job.call_args
    assert call_args.args[0] == SyncJobType.RADARR_IMPORT.value
    assert call_args.kwargs["trigger"] == "cron"


async def test_put_is_enabled_reflects_service_config(
    client_with_db, session_for_test, monkeypatch
) -> None:
    """PUT response is_enabled=True when the required service is configured."""
    import app.utils.encryption as enc_module

    _FERNET_KEY = "Yw1UOJf9F_KlNf3Px34rRqhSPmhbqTKXQiANfC-rFzI="
    monkeypatch.setenv("ENCRYPTION_KEY", _FERNET_KEY)
    monkeypatch.setattr(enc_module, "_fernet", None)

    from app.dependencies.scheduler import get_scheduler
    from app.main import app
    from app.services import service_config_repository as repo

    # Add RADARR service config
    await repo.upsert_config(
        session_for_test, ServiceType.RADARR, "http://radarr:7878", "testapikey"
    )
    await session_for_test.commit()

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        response = await client_with_db.put(
            "/api/v1/settings/schedules/radarr_import",
            json={"preset": "daily"},
        )
    finally:
        app.dependency_overrides.pop(get_scheduler, None)

    assert response.status_code == 200
    assert response.json()["is_enabled"] is True


async def test_put_is_enabled_false_when_service_not_configured(
    client_with_db,
) -> None:
    """PUT response is_enabled=False when no service config exists."""
    from app.dependencies.scheduler import get_scheduler
    from app.main import app

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        response = await client_with_db.put(
            "/api/v1/settings/schedules/radarr_import",
            json={"preset": "daily"},
        )
    finally:
        app.dependency_overrides.pop(get_scheduler, None)

    assert response.status_code == 200
    assert response.json()["is_enabled"] is False


async def test_put_invalid_job_type_returns_422(client_with_db) -> None:
    """PUT with unknown job_type → 422."""
    from app.dependencies.scheduler import get_scheduler
    from app.main import app

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        response = await client_with_db.put(
            "/api/v1/settings/schedules/nonexistent_job",
            json={"preset": "daily"},
        )
    finally:
        app.dependency_overrides.pop(get_scheduler, None)

    assert response.status_code == 422


async def test_full_schedule_lifecycle(client_with_db, session_for_test) -> None:
    """Create → verify → update → verify — full lifecycle for one job."""
    from app.dependencies.scheduler import get_scheduler
    from app.main import app

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        # Step 1: Set daily
        resp1 = await client_with_db.put(
            "/api/v1/settings/schedules/sonarr_import",
            json={"preset": "daily"},
        )
        assert resp1.status_code == 200
        assert resp1.json()["preset"] == "daily"

        # Step 2: Verify via GET
        get_resp = await client_with_db.get("/api/v1/settings/schedules")
        schedules = {s["job_type"]: s for s in get_resp.json()["schedules"]}
        assert schedules["sonarr_import"]["preset"] == "daily"

        # Step 3: Update to weekly
        resp2 = await client_with_db.put(
            "/api/v1/settings/schedules/sonarr_import",
            json={"preset": "weekly"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["preset"] == "weekly"
        assert resp2.json()["cron_expression"].endswith("0")

        # Step 4: Verify DB has only 1 row
        result = await session_for_test.execute(
            select(SyncSchedule).where(SyncSchedule.job_type == SyncJobType.SONARR_IMPORT)
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].preset == SchedulePreset.WEEKLY
    finally:
        app.dependency_overrides.pop(get_scheduler, None)


async def test_get_returns_all_7_job_type_values(client_with_db) -> None:
    """GET response contains every SyncJobType enum value exactly once."""
    from app.dependencies.scheduler import get_scheduler
    from app.main import app

    mock_scheduler = _mock_scheduler_with_no_jobs()
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler

    try:
        response = await client_with_db.get("/api/v1/settings/schedules")
    finally:
        app.dependency_overrides.pop(get_scheduler, None)

    assert response.status_code == 200
    returned = {s["job_type"] for s in response.json()["schedules"]}
    expected = {jt.value for jt in SyncJobType}
    assert returned == expected
