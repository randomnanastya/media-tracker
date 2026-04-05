"""Unit tests for POST /api/v1/sync/trigger/{job_type} endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import ServiceType, SyncJobType
from tests.factories import SyncScheduleFactory


def make_fake_registry(mock_job: AsyncMock) -> dict:
    return {SyncJobType.RADARR_IMPORT: (mock_job, ServiceType.RADARR)}


# ---------------------------------------------------------------------------
# POST /api/v1/sync/trigger/{job_type}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_sync_returns_202(async_client, mock_session) -> None:
    """Config found, is_running=False → 202 with expected body."""
    config = MagicMock()
    mock_job = AsyncMock()

    with (
        patch("app.api.sync.JOB_REGISTRY", make_fake_registry(mock_job)),
        patch(
            "app.api.sync.config_repo.get_config_by_service",
            new_callable=AsyncMock,
            return_value=config,
        ),
        patch(
            "app.api.sync.schedule_repo.get_schedule_by_job",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        response = await async_client.post("/api/v1/sync/trigger/radarr_import")

    assert response.status_code == 202
    data = response.json()
    assert data["job_type"] == "radarr_import"
    assert data["message"] == "Sync job started"


@pytest.mark.asyncio
async def test_trigger_sync_service_not_configured_returns_422(async_client, mock_session) -> None:
    """config_repo.get_config_by_service returns None → 422 with detail."""
    mock_job = AsyncMock()

    with (
        patch("app.api.sync.JOB_REGISTRY", make_fake_registry(mock_job)),
        patch(
            "app.api.sync.config_repo.get_config_by_service",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        response = await async_client.post("/api/v1/sync/trigger/radarr_import")

    assert response.status_code == 422
    assert response.json()["detail"] == "Service not configured"


@pytest.mark.asyncio
async def test_trigger_sync_job_already_running_returns_409(async_client, mock_session) -> None:
    """Config found, schedule.is_running=True → 409 with detail."""
    config = MagicMock()
    mock_job = AsyncMock()
    running_schedule = SyncScheduleFactory.build(
        job_type=SyncJobType.RADARR_IMPORT, is_running=True
    )

    with (
        patch("app.api.sync.JOB_REGISTRY", make_fake_registry(mock_job)),
        patch(
            "app.api.sync.config_repo.get_config_by_service",
            new_callable=AsyncMock,
            return_value=config,
        ),
        patch(
            "app.api.sync.schedule_repo.get_schedule_by_job",
            new_callable=AsyncMock,
            return_value=running_schedule,
        ),
    ):
        response = await async_client.post("/api/v1/sync/trigger/radarr_import")

    assert response.status_code == 409
    assert response.json()["detail"] == "Job is already running"


@pytest.mark.asyncio
async def test_trigger_sync_invalid_job_type_returns_422(async_client, mock_session) -> None:
    """Unknown job_type path param → 422 (FastAPI enum validation)."""
    response = await async_client.post("/api/v1/sync/trigger/nonexistent_job")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_trigger_sync_creates_asyncio_task(async_client, mock_session) -> None:
    """On success the job function is called exactly once."""
    config = MagicMock()
    mock_job = AsyncMock()
    not_running_schedule = SyncScheduleFactory.build(
        job_type=SyncJobType.RADARR_IMPORT, is_running=False
    )

    with (
        patch("app.api.sync.JOB_REGISTRY", make_fake_registry(mock_job)),
        patch(
            "app.api.sync.config_repo.get_config_by_service",
            new_callable=AsyncMock,
            return_value=config,
        ),
        patch(
            "app.api.sync.schedule_repo.get_schedule_by_job",
            new_callable=AsyncMock,
            return_value=not_running_schedule,
        ),
    ):
        response = await async_client.post("/api/v1/sync/trigger/radarr_import")

    assert response.status_code == 202
    mock_job.assert_called_once()
