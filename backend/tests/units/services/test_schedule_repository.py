"""Tests for app.services.schedule_repository."""

from unittest.mock import AsyncMock, Mock

from app.models import SchedulePreset, SyncJobType, SyncSchedule
from app.services import schedule_repository as repo
from tests.factories import SyncScheduleFactory


class TestGetAllSchedules:
    async def test_returns_list_of_schedules(self, mock_session: AsyncMock) -> None:
        s1 = SyncScheduleFactory.build(job_type=SyncJobType.RADARR_IMPORT)
        s2 = SyncScheduleFactory.build(job_type=SyncJobType.SONARR_IMPORT)
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [s1, s2]
        mock_session.execute.return_value = mock_result

        result = await repo.get_all_schedules(mock_session)

        assert len(result) == 2

    async def test_returns_empty_list(self, mock_session: AsyncMock) -> None:
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_all_schedules(mock_session)

        assert result == []

    async def test_returns_correct_objects(self, mock_session: AsyncMock) -> None:
        s1 = SyncScheduleFactory.build(job_type=SyncJobType.RADARR_IMPORT)
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [s1]
        mock_session.execute.return_value = mock_result

        result = await repo.get_all_schedules(mock_session)

        assert result[0] is s1

    async def test_returns_list_type(self, mock_session: AsyncMock) -> None:
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_all_schedules(mock_session)

        assert isinstance(result, list)


class TestGetScheduleByJob:
    async def test_returns_schedule_when_found(self, mock_session: AsyncMock) -> None:
        schedule = SyncScheduleFactory.build(job_type=SyncJobType.RADARR_IMPORT)
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = schedule
        mock_session.execute.return_value = mock_result

        result = await repo.get_schedule_by_job(mock_session, SyncJobType.RADARR_IMPORT)

        assert result is schedule

    async def test_returns_none_when_not_found(self, mock_session: AsyncMock) -> None:
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_schedule_by_job(mock_session, SyncJobType.RADARR_IMPORT)

        assert result is None

    async def test_execute_is_called_once(self, mock_session: AsyncMock) -> None:
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        await repo.get_schedule_by_job(mock_session, SyncJobType.SONARR_IMPORT)

        mock_session.execute.assert_called_once()

    async def test_different_job_types_return_independently(self, mock_session: AsyncMock) -> None:
        sonarr_schedule = SyncScheduleFactory.build(job_type=SyncJobType.SONARR_IMPORT)
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = sonarr_schedule
        mock_session.execute.return_value = mock_result

        result = await repo.get_schedule_by_job(mock_session, SyncJobType.SONARR_IMPORT)

        assert result is sonarr_schedule
        assert result.job_type == SyncJobType.SONARR_IMPORT


class TestUpsertSchedule:
    async def test_creates_new_schedule_when_not_exists(self, mock_session: AsyncMock) -> None:
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

    async def test_updates_existing_schedule(self, mock_session: AsyncMock) -> None:
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

    async def test_update_returns_same_object(self, mock_session: AsyncMock) -> None:
        existing = SyncScheduleFactory.build(job_type=SyncJobType.RADARR_IMPORT)
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = existing
        mock_session.execute.return_value = mock_result

        result = await repo.upsert_schedule(
            mock_session, SyncJobType.RADARR_IMPORT, SchedulePreset.MONTHLY, "10 1 1 * *"
        )

        assert result is existing

    async def test_create_does_not_call_session_add_twice(self, mock_session: AsyncMock) -> None:
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        await repo.upsert_schedule(
            mock_session, SyncJobType.SONARR_IMPORT, SchedulePreset.DAILY, "40 1 * * *"
        )

        assert mock_session.add.call_count == 1

    async def test_does_not_commit_internally(self, mock_session: AsyncMock) -> None:
        # upsert should NOT commit — caller is responsible
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        await repo.upsert_schedule(
            mock_session, SyncJobType.RADARR_IMPORT, SchedulePreset.DAILY, "10 22 * * *"
        )

        mock_session.commit.assert_not_called()

    async def test_update_custom_preset(self, mock_session: AsyncMock) -> None:
        existing = SyncScheduleFactory.build(
            job_type=SyncJobType.JELLYFIN_USERS_IMPORT,
            preset=SchedulePreset.MONTHLY,
            cron_expression="55 8 1 * *",
        )
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = existing
        mock_session.execute.return_value = mock_result

        result = await repo.upsert_schedule(
            mock_session,
            SyncJobType.JELLYFIN_USERS_IMPORT,
            SchedulePreset.CUSTOM,
            "0 4 * * 3",
        )

        assert result.preset == SchedulePreset.CUSTOM
        assert result.cron_expression == "0 4 * * 3"


class TestSetRunningStatus:
    async def test_executes_update_query(self, mock_session: AsyncMock) -> None:
        await repo.set_running_status(mock_session, SyncJobType.RADARR_IMPORT, True)

        mock_session.execute.assert_called_once()

    async def test_execute_called_for_false_status(self, mock_session: AsyncMock) -> None:
        await repo.set_running_status(mock_session, SyncJobType.RADARR_IMPORT, False)

        mock_session.execute.assert_called_once()

    async def test_does_not_commit(self, mock_session: AsyncMock) -> None:
        await repo.set_running_status(mock_session, SyncJobType.SONARR_IMPORT, True)

        mock_session.commit.assert_not_called()

    async def test_called_for_every_job_type(self, mock_session: AsyncMock) -> None:
        for job_type in SyncJobType:
            mock_session.reset_mock()
            await repo.set_running_status(mock_session, job_type, True)
            mock_session.execute.assert_called_once()


class TestUpdateLastRun:
    async def test_executes_update_with_last_run_at(self, mock_session: AsyncMock) -> None:
        await repo.update_last_run(mock_session, SyncJobType.RADARR_IMPORT)

        mock_session.execute.assert_called_once()

    async def test_does_not_commit(self, mock_session: AsyncMock) -> None:
        await repo.update_last_run(mock_session, SyncJobType.SONARR_IMPORT)

        mock_session.commit.assert_not_called()

    async def test_called_for_jellyfin_job_type(self, mock_session: AsyncMock) -> None:
        await repo.update_last_run(mock_session, SyncJobType.JELLYFIN_USERS_IMPORT)

        mock_session.execute.assert_called_once()

    async def test_execute_called_exactly_once_per_call(self, mock_session: AsyncMock) -> None:
        await repo.update_last_run(mock_session, SyncJobType.RADARR_IMPORT)
        await repo.update_last_run(mock_session, SyncJobType.SONARR_IMPORT)

        assert mock_session.execute.call_count == 2
