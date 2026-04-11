"""Unit tests for app.services.media_service (no real DB)."""

from unittest.mock import AsyncMock, Mock

from app.schemas.media import MediaListResponse
from app.services.media_service import get_media_list


def _make_session(rows: list[dict]) -> AsyncMock:
    """Build AsyncMock that mimics session.execute().mappings().all() path."""
    session = AsyncMock()
    mappings_mock = Mock()
    mappings_mock.all.return_value = rows
    execute_result = Mock()
    execute_result.mappings.return_value = mappings_mock
    session.execute = AsyncMock(return_value=execute_result)
    return session


def _movie_row(
    media_id: int = 1,
    title: str = "Test Movie",
    movie_status: str | None = None,
    movie_wh_user_id: int | None = None,
) -> dict:
    return {
        "id": media_id,
        "title": title,
        "media_type": "MOVIE",
        "year": 2023,
        "genres": ["Action"],
        "poster_url": None,
        "rating": 7.5,
        "movie_status": movie_status,
        "movie_wh_user_id": movie_wh_user_id,
        "total_count": None,
        "watched_count": None,
        "watching_count": None,
        "dropped_count": None,
    }


def _series_row(
    media_id: int = 2,
    title: str = "Test Series",
    total_count: int = 0,
    watched_count: int = 0,
    watching_count: int = 0,
    dropped_count: int = 0,
) -> dict:
    return {
        "id": media_id,
        "title": title,
        "media_type": "SERIES",
        "year": 2022,
        "genres": ["Drama"],
        "poster_url": None,
        "rating": 8.0,
        "movie_status": None,
        "movie_wh_user_id": None,
        "total_count": total_count,
        "watched_count": watched_count,
        "watching_count": watching_count,
        "dropped_count": dropped_count,
    }


class TestGetMediaListEmpty:
    async def test_empty_db_returns_empty_response(self) -> None:
        session = _make_session([])
        result = await get_media_list(session)
        assert result == MediaListResponse(items=[], total=0)

    async def test_empty_db_total_is_zero(self) -> None:
        session = _make_session([])
        result = await get_media_list(session)
        assert result.total == 0

    async def test_empty_db_items_is_empty_list(self) -> None:
        session = _make_session([])
        result = await get_media_list(session)
        assert result.items == []


class TestMovieWithoutWatchHistory:
    async def test_movie_without_watch_history_has_none_status(self) -> None:
        row = _movie_row(movie_status=None)
        session = _make_session([row])
        result = await get_media_list(session)
        assert result.items[0].watch_status is None

    async def test_movie_without_watch_history_total_is_one(self) -> None:
        row = _movie_row()
        session = _make_session([row])
        result = await get_media_list(session)
        assert result.total == 1

    async def test_movie_without_watch_history_media_type_is_movie(self) -> None:
        row = _movie_row()
        session = _make_session([row])
        result = await get_media_list(session)
        assert result.items[0].media_type == "movie"


class TestMovieWithWatchedStatus:
    async def test_movie_with_watched_status(self) -> None:
        row = _movie_row(movie_status="watched", movie_wh_user_id=1)
        session = _make_session([row])
        result = await get_media_list(session)
        assert result.items[0].watch_status == "watched"

    async def test_movie_with_watched_status_total_is_one(self) -> None:
        row = _movie_row(movie_status="watched", movie_wh_user_id=1)
        session = _make_session([row])
        result = await get_media_list(session)
        assert result.total == 1


class TestSeriesWatchStatus:
    async def test_series_with_one_watched_one_planned_episode_returns_watching(self) -> None:
        row = _series_row(total_count=2, watched_count=1, watching_count=0, dropped_count=0)
        session = _make_session([row])
        result = await get_media_list(session)
        assert result.items[0].watch_status == "watching"

    async def test_series_all_episodes_watched_returns_watched(self) -> None:
        row = _series_row(total_count=2, watched_count=2, watching_count=0, dropped_count=0)
        session = _make_session([row])
        result = await get_media_list(session)
        assert result.items[0].watch_status == "watched"

    async def test_series_no_episodes_watched_returns_planned(self) -> None:
        row = _series_row(total_count=3, watched_count=0, watching_count=0, dropped_count=0)
        session = _make_session([row])
        result = await get_media_list(session)
        assert result.items[0].watch_status == "planned"

    async def test_series_only_dropped_returns_dropped(self) -> None:
        row = _series_row(total_count=2, watched_count=0, watching_count=0, dropped_count=1)
        session = _make_session([row])
        result = await get_media_list(session)
        assert result.items[0].watch_status == "dropped"

    async def test_series_zero_total_episodes_returns_none_status(self) -> None:
        row = _series_row(total_count=0)
        session = _make_session([row])
        result = await get_media_list(session)
        assert result.items[0].watch_status is None


class TestFilterByType:
    async def test_filter_type_movie_returns_only_movies(self) -> None:
        movie_row = _movie_row(media_id=1, title="Movie")
        # SQL applies the type filter — mock only returns what DB would return
        session = _make_session([movie_row])
        result = await get_media_list(session, media_type="movie")
        assert all(item.media_type == "movie" for item in result.items)

    async def test_filter_type_movie_excludes_series(self) -> None:
        movie_row = _movie_row(media_id=1, title="Movie")
        # SQL filter is applied by the DB, but the service still processes what comes back.
        # When media_type filter is "movie", DB only returns movie rows — simulate that.
        session = _make_session([movie_row])
        result = await get_media_list(session, media_type="movie")
        assert result.total == 1
        assert result.items[0].title == "Movie"

    async def test_filter_type_series_returns_only_series(self) -> None:
        series_row = _series_row(media_id=2, title="Series")
        session = _make_session([series_row])
        result = await get_media_list(session, media_type="series")
        assert result.total == 1
        assert result.items[0].media_type == "series"


class TestFilterByStatus:
    async def test_filter_status_watched_returns_only_watched(self) -> None:
        watched_row = _movie_row(media_id=1, title="Watched Movie", movie_status="watched")
        planned_row = _movie_row(media_id=2, title="Planned Movie", movie_status="planned")
        session = _make_session([watched_row, planned_row])
        result = await get_media_list(session, status="watched")
        assert result.total == 1
        assert result.items[0].watch_status == "watched"

    async def test_filter_status_watched_excludes_other_statuses(self) -> None:
        planned_row = _movie_row(media_id=1, title="Planned", movie_status="planned")
        no_status_row = _movie_row(media_id=2, title="No Status", movie_status=None)
        session = _make_session([planned_row, no_status_row])
        result = await get_media_list(session, status="watched")
        assert result.total == 0
        assert result.items == []

    async def test_filter_status_planned_returns_matching(self) -> None:
        planned_row = _movie_row(media_id=1, title="Planned", movie_status="planned")
        watched_row = _movie_row(media_id=2, title="Watched", movie_status="watched")
        session = _make_session([planned_row, watched_row])
        result = await get_media_list(session, status="planned")
        assert result.total == 1
        assert result.items[0].title == "Planned"

    async def test_filter_status_none_returns_all(self) -> None:
        watched_row = _movie_row(media_id=1, title="Watched", movie_status="watched")
        planned_row = _movie_row(media_id=2, title="Planned", movie_status="planned")
        session = _make_session([watched_row, planned_row])
        result = await get_media_list(session, status=None)
        assert result.total == 2
