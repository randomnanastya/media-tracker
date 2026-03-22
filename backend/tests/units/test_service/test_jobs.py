"""Unit tests for app.services.jobs — log_job_execution decorator and job functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import SyncJobType


class TestLogJobExecution:
    """Tests for the log_job_execution decorator behavior."""

    async def test_calls_wrapped_function(self) -> None:
        """Decorated function is called once when decorator is applied."""
        from app.services.jobs import log_job_execution

        mock_func = AsyncMock()
        mock_func.__name__ = "unregistered_func"
        wrapped = log_job_execution(mock_func)

        with patch("app.services.jobs.AsyncSessionLocal"):
            # No job_type in registry → no DB calls for session
            await wrapped()

        mock_func.assert_called_once()

    async def test_preserves_function_name(self) -> None:
        """Decorator preserves __name__ of the wrapped function."""
        from app.services.jobs import log_job_execution

        async def my_job() -> None:
            pass

        wrapped = log_job_execution(my_job)
        assert wrapped.__name__ == "my_job"

    async def test_reraises_exception_from_wrapped_function(self) -> None:
        """Exception inside decorated function is re-raised."""
        from app.services.jobs import log_job_execution

        async def failing_func() -> None:
            raise ValueError("job failed")

        failing_func.__name__ = "unregistered_failing"
        wrapped = log_job_execution(failing_func)

        with (
            patch("app.services.jobs.AsyncSessionLocal"),
            pytest.raises(ValueError, match="job failed"),
        ):
            await wrapped()

    async def test_sets_running_true_before_calling_func(self) -> None:
        """is_running=True is set before the job function executes."""
        from app.services.jobs import _JOB_FUNC_TO_TYPE, log_job_execution

        call_order: list[str] = []
        mock_set_running = AsyncMock(side_effect=lambda *a, **kw: call_order.append("set_running"))

        async def tracked_func() -> None:
            call_order.append("func_called")

        # Find a registered job name to test the DB path
        # We register the func name in _JOB_FUNC_TO_TYPE directly
        tracked_func.__name__ = "_test_tracked_func_unique"
        _JOB_FUNC_TO_TYPE["_test_tracked_func_unique"] = SyncJobType.RADARR_IMPORT

        try:
            wrapped = log_job_execution(tracked_func)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            with (
                patch("app.services.jobs.schedule_repo.set_running_status", mock_set_running),
                patch("app.services.jobs.schedule_repo.update_last_run", AsyncMock()),
                patch(
                    "app.services.jobs.AsyncSessionLocal",
                    return_value=mock_session,
                ),
            ):
                await wrapped()

            assert call_order[0] == "set_running"
            assert call_order[1] == "func_called"
        finally:
            _JOB_FUNC_TO_TYPE.pop("_test_tracked_func_unique", None)

    async def test_sets_running_false_in_finally_on_success(self) -> None:
        """is_running=False and last_run updated in finally block after success."""
        from app.services.jobs import _JOB_FUNC_TO_TYPE, log_job_execution

        mock_set_running = AsyncMock()
        mock_update_last_run = AsyncMock()

        async def success_func() -> None:
            pass

        success_func.__name__ = "_test_success_func_unique"
        _JOB_FUNC_TO_TYPE["_test_success_func_unique"] = SyncJobType.SONARR_IMPORT

        try:
            wrapped = log_job_execution(success_func)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            with (
                patch("app.services.jobs.schedule_repo.set_running_status", mock_set_running),
                patch("app.services.jobs.schedule_repo.update_last_run", mock_update_last_run),
                patch("app.services.jobs.AsyncSessionLocal", return_value=mock_session),
            ):
                await wrapped()

            # set_running called twice: True before, False in finally
            assert mock_set_running.call_count == 2
            calls = mock_set_running.call_args_list
            first_call_args = calls[0]
            last_call_args = calls[1]
            first_is_running = (
                first_call_args.args[2]
                if len(first_call_args.args) > 2
                else first_call_args.kwargs.get("is_running")
            )
            last_is_running = (
                last_call_args.args[2]
                if len(last_call_args.args) > 2
                else last_call_args.kwargs.get("is_running")
            )
            assert first_is_running is True
            assert last_is_running is False
            mock_update_last_run.assert_called_once()
        finally:
            _JOB_FUNC_TO_TYPE.pop("_test_success_func_unique", None)

    async def test_sets_running_false_in_finally_on_failure(self) -> None:
        """is_running=False and last_run updated in finally block even after failure."""
        from app.services.jobs import _JOB_FUNC_TO_TYPE, log_job_execution

        mock_set_running = AsyncMock()
        mock_update_last_run = AsyncMock()

        async def failing_func() -> None:
            raise RuntimeError("oops")

        failing_func.__name__ = "_test_fail_func_unique"
        _JOB_FUNC_TO_TYPE["_test_fail_func_unique"] = SyncJobType.RADARR_IMPORT

        try:
            wrapped = log_job_execution(failing_func)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            with (
                patch("app.services.jobs.schedule_repo.set_running_status", mock_set_running),
                patch("app.services.jobs.schedule_repo.update_last_run", mock_update_last_run),
                patch("app.services.jobs.AsyncSessionLocal", return_value=mock_session),
                pytest.raises(RuntimeError),
            ):
                await wrapped()

            mock_update_last_run.assert_called_once()
            # Last call to set_running should be False
            last_call = mock_set_running.call_args_list[-1]
            is_running_value = (
                last_call.args[2] if len(last_call.args) > 2 else last_call.kwargs.get("is_running")
            )
            assert is_running_value is False
        finally:
            _JOB_FUNC_TO_TYPE.pop("_test_fail_func_unique", None)

    async def test_no_db_calls_for_unregistered_function(self) -> None:
        """Function not in _JOB_FUNC_TO_TYPE does not trigger DB session usage."""
        from app.services.jobs import log_job_execution

        mock_set_running = AsyncMock()

        async def unregistered() -> None:
            pass

        unregistered.__name__ = "_truly_unregistered_xyz"
        wrapped = log_job_execution(unregistered)

        with patch("app.services.jobs.schedule_repo.set_running_status", mock_set_running):
            await wrapped()

        mock_set_running.assert_not_called()


class TestJobFunctionsGracefulSkip:
    """Tests for graceful skip behavior when service is not configured."""

    async def test_radarr_import_job_skips_when_not_configured(self) -> None:
        """radarr_import_job returns early without calling import if config is missing."""
        from app.services.jobs import radarr_import_job

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.services.jobs.AsyncSessionLocal", return_value=mock_session),
            patch(
                "app.services.jobs.get_config_by_service",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("app.services.jobs._run_radarr_import", new_callable=AsyncMock) as mock_run,
        ):
            await radarr_import_job()

        mock_run.assert_not_called()

    async def test_radarr_import_job_runs_when_configured(self) -> None:
        """radarr_import_job calls _run_radarr_import when config exists."""
        from app.services.jobs import radarr_import_job

        mock_config = MagicMock()
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.services.jobs.AsyncSessionLocal", return_value=mock_session),
            patch(
                "app.services.jobs.get_config_by_service",
                new_callable=AsyncMock,
                return_value=mock_config,
            ),
            patch("app.services.jobs._run_radarr_import", new_callable=AsyncMock) as mock_run,
        ):
            await radarr_import_job()

        mock_run.assert_called_once()

    async def test_sonarr_import_job_skips_when_not_configured(self) -> None:
        """sonarr_import_job returns early without calling import if config is missing."""
        from app.services.jobs import sonarr_import_job

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.services.jobs.AsyncSessionLocal", return_value=mock_session),
            patch(
                "app.services.jobs.get_config_by_service",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("app.services.jobs._run_sonarr_import", new_callable=AsyncMock) as mock_run,
        ):
            await sonarr_import_job()

        mock_run.assert_not_called()

    async def test_jellyfin_import_users_job_skips_when_not_configured(self) -> None:
        """jellyfin_import_users_job skips when jellyfin config missing."""
        from app.services.jobs import jellyfin_import_users_job

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.services.jobs.AsyncSessionLocal", return_value=mock_session),
            patch(
                "app.services.jobs.get_config_by_service",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.jobs._run_jellyfin_import_users", new_callable=AsyncMock
            ) as mock_run,
        ):
            await jellyfin_import_users_job()

        mock_run.assert_not_called()

    async def test_jellyfin_import_movies_job_skips_when_not_configured(self) -> None:
        """jellyfin_import_movies_job skips when jellyfin config missing."""
        from app.services.jobs import jellyfin_import_movies_job

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.services.jobs.AsyncSessionLocal", return_value=mock_session),
            patch(
                "app.services.jobs.get_config_by_service",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.jobs._run_jellyfin_import_movies", new_callable=AsyncMock
            ) as mock_run,
        ):
            await jellyfin_import_movies_job()

        mock_run.assert_not_called()

    async def test_jellyfin_import_series_job_skips_when_not_configured(self) -> None:
        """jellyfin_import_series_job skips when jellyfin config missing."""
        from app.services.jobs import jellyfin_import_series_job

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.services.jobs.AsyncSessionLocal", return_value=mock_session),
            patch(
                "app.services.jobs.get_config_by_service",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.jobs._run_jellyfin_import_series", new_callable=AsyncMock
            ) as mock_run,
        ):
            await jellyfin_import_series_job()

        mock_run.assert_not_called()

    async def test_jellyfin_sync_movie_watch_history_job_skips_when_not_configured(self) -> None:
        """jellyfin_sync_movie_watch_history_job skips when jellyfin config missing."""
        from app.services.jobs import jellyfin_sync_movie_watch_history_job

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.services.jobs.AsyncSessionLocal", return_value=mock_session),
            patch(
                "app.services.jobs.get_config_by_service",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.jobs._run_jellyfin_sync_movie_watch_history",
                new_callable=AsyncMock,
            ) as mock_run,
        ):
            await jellyfin_sync_movie_watch_history_job()

        mock_run.assert_not_called()

    async def test_jellyfin_sync_series_watch_history_job_skips_when_not_configured(self) -> None:
        """jellyfin_sync_series_watch_history_job skips when jellyfin config missing."""
        from app.services.jobs import jellyfin_sync_series_watch_history_job

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.services.jobs.AsyncSessionLocal", return_value=mock_session),
            patch(
                "app.services.jobs.get_config_by_service",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.jobs._run_jellyfin_sync_series_watch_history",
                new_callable=AsyncMock,
            ) as mock_run,
        ):
            await jellyfin_sync_series_watch_history_job()

        mock_run.assert_not_called()

    async def test_sonarr_import_job_runs_when_configured(self) -> None:
        """sonarr_import_job calls _run_sonarr_import when config exists."""
        from app.services.jobs import sonarr_import_job

        mock_config = MagicMock()
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.services.jobs.AsyncSessionLocal", return_value=mock_session),
            patch(
                "app.services.jobs.get_config_by_service",
                new_callable=AsyncMock,
                return_value=mock_config,
            ),
            patch("app.services.jobs._run_sonarr_import", new_callable=AsyncMock) as mock_run,
        ):
            await sonarr_import_job()

        mock_run.assert_called_once()


class TestJobFuncToTypeMapping:
    """Tests for _JOB_FUNC_TO_TYPE reverse mapping completeness."""

    def test_all_run_functions_are_in_mapping(self) -> None:
        """All _run_* functions have a corresponding entry in _JOB_FUNC_TO_TYPE."""
        from app.services.jobs import (
            _JOB_FUNC_TO_TYPE,
            _run_jellyfin_import_movies,
            _run_jellyfin_import_series,
            _run_jellyfin_import_users,
            _run_jellyfin_sync_movie_watch_history,
            _run_jellyfin_sync_series_watch_history,
            _run_radarr_import,
            _run_sonarr_import,
        )

        run_funcs = [
            _run_radarr_import,
            _run_sonarr_import,
            _run_jellyfin_import_users,
            _run_jellyfin_import_movies,
            _run_jellyfin_import_series,
            _run_jellyfin_sync_movie_watch_history,
            _run_jellyfin_sync_series_watch_history,
        ]

        for func in run_funcs:
            assert (
                func.__name__ in _JOB_FUNC_TO_TYPE
            ), f"{func.__name__} not found in _JOB_FUNC_TO_TYPE"

    def test_mapping_covers_all_sync_job_types(self) -> None:
        """_JOB_FUNC_TO_TYPE maps to every SyncJobType value."""
        from app.services.jobs import _JOB_FUNC_TO_TYPE

        mapped_job_types = set(_JOB_FUNC_TO_TYPE.values())
        all_job_types = set(SyncJobType)
        assert mapped_job_types == all_job_types

    def test_mapping_has_no_duplicate_job_types(self) -> None:
        """Each SyncJobType appears exactly once in the mapping values."""
        from app.services.jobs import _JOB_FUNC_TO_TYPE

        values = list(_JOB_FUNC_TO_TYPE.values())
        assert len(values) == len(set(values))
