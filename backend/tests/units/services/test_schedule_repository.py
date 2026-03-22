"""Tests for app.services.schedule_repository."""

from unittest.mock import AsyncMock, Mock

from app.models import SchedulePreset, SyncJobType, SyncSchedule
from app.services import schedule_repository as repo
from tests.factories import SyncScheduleFactory


class TestGetAllSchedules:
    async def test_returns_list_of_schedules(self, mock_session: AsyncMock):
        s1 = SyncScheduleFactory.build(job_type=SyncJobType.RADARR_IMPORT)
        s2 = SyncScheduleFactory.build(job_type=SyncJobType.SONARR_IMPORT)
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [s1, s2]
        mock_session.execute.return_value = mock_result

        result = await repo.get_all_schedules(mock_session)

        assert len(result) == 2

    async def test_returns_empty_list(self, mock_session: AsyncMock):
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_all_schedules(mock_session)

        assert result == []


class TestGetScheduleByJob:
    async def test_returns_schedule_when_found(self, mock_session: AsyncMock):
        schedule = SyncScheduleFactory.build(job_type=SyncJobType.RADARR_IMPORT)
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = schedule
        mock_session.execute.return_value = mock_result

        result = await repo.get_schedule_by_job(mock_session, SyncJobType.RADARR_IMPORT)

        assert result is schedule

    async def test_returns_none_when_not_found(self, mock_session: AsyncMock):
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_schedule_by_job(mock_session, SyncJobType.RADARR_IMPORT)

        assert result is None


class TestUpsertSchedule:
    async def test_creates_new_schedule_when_not_exists(self, mock_session: AsyncMock):
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.upsert_schedule(
            mock_session, SyncJobType.RADARR_IMPORT, SchedulePreset.DAILY, "10 1 * * *"
        )

        mock_session.add.assert_called_once()
        assert isinstance(result, SyncSchedule)
        assert result.job_type == SyncJobType.RADARR_IMPORT
        assert result.preset == SchedulePreset.DAILY
        assert result.cron_expression == "10 1 * * *"

    async def test_updates_existing_schedule(self, mock_session: AsyncMock):
        existing = SyncScheduleFactory.build(
            job_type=SyncJobType.RADARR_IMPORT,
            preset=SchedulePreset.DAILY,
            cron_expression="10 1 * * *",
        )
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = existing
        mock_session.execute.return_value = mock_result

        result = await repo.upsert_schedule(
            mock_session, SyncJobType.RADARR_IMPORT, SchedulePreset.WEEKLY, "10 1 * * 0"
        )

        mock_session.add.assert_not_called()
        assert result.preset == SchedulePreset.WEEKLY
        assert result.cron_expression == "10 1 * * 0"


class TestSetRunningStatus:
    async def test_executes_update_query(self, mock_session: AsyncMock):
        await repo.set_running_status(mock_session, SyncJobType.RADARR_IMPORT, True)

        mock_session.execute.assert_called_once()


class TestUpdateLastRun:
    async def test_executes_update_with_last_run_at(self, mock_session: AsyncMock):
        await repo.update_last_run(mock_session, SyncJobType.RADARR_IMPORT)

        mock_session.execute.assert_called_once()
