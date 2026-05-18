"""Unit tests for update_tmdb_metadata_service."""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.client.tmdb_bridge_client import TmdbBridgeClientError
from app.models.media import MovieStatus
from app.schemas.error_codes import TmdbBridgeErrorCode
from app.schemas.tmdb_bridge import TmdbBridgeMovieResponse, TmdbGenre
from app.services.update_tmdb_metadata_service import (
    _apply_tmdb_update,
    update_movies_tmdb_metadata,
)
from tests.factories import MediaFactory, MovieFactory


def _make_movie(**kwargs):  # type: ignore[no-untyped-def]
    media = MediaFactory.build(title="Original Title")
    return MovieFactory.build(media=media, **kwargs)


def _make_payload(**kwargs) -> TmdbBridgeMovieResponse:
    defaults: dict = {
        "tmdb_id": "123",
        "title": "New Title",
        "original_title": "New Original",
        "overview": "Some overview",
        "backdrop_path": "/backdrop.jpg",
        "poster_url": "https://img.tmdb.org/poster.jpg",
        "status": "Released",
        "release_date": date(2024, 1, 15),
        "vote_average": 8.5,
        "vote_count": 1000,
        "genres": [TmdbGenre(id=28, name="Action")],
    }
    defaults.update(kwargs)
    return TmdbBridgeMovieResponse(**defaults)


# --- _apply_tmdb_update ---


def test_title_overwrite() -> None:
    movie = _make_movie()
    movie.media.title = "Old Title"
    payload = _make_payload(title="New Title")

    changed = _apply_tmdb_update(movie, payload)

    assert changed is True
    assert movie.media.title == "New Title"


def test_title_no_change() -> None:
    movie = _make_movie(
        original_title="orig",
        overview="text",
        backdrop_path="/b.jpg",
        poster_url="http://p.jpg",
        status=MovieStatus.RELEASED,
        genres=["Action"],
        rating_value=8.5,
        rating_votes=1000,
    )
    movie.media.title = "Same Title"
    movie.media.release_date = datetime(2024, 1, 15, tzinfo=UTC)
    payload = _make_payload(
        title="Same Title",
        original_title="orig",
        overview="text",
        backdrop_path="/b.jpg",
        poster_url="http://p.jpg",
        status="Released",
        release_date=date(2024, 1, 15),
        vote_average=8.5,
        vote_count=1000,
        genres=[TmdbGenre(id=28, name="Action")],
    )

    changed = _apply_tmdb_update(movie, payload)

    assert changed is False


def test_original_title_fill_if_empty() -> None:
    movie = _make_movie(original_title=None)
    payload = _make_payload(original_title="The Original")

    _apply_tmdb_update(movie, payload)

    assert movie.original_title == "The Original"


def test_original_title_keep_existing() -> None:
    movie = _make_movie(original_title="Already Set")
    payload = _make_payload(original_title="Different")

    _apply_tmdb_update(movie, payload)

    assert movie.original_title == "Already Set"


def test_genres_fill_if_empty() -> None:
    movie = _make_movie(genres=None)
    payload = _make_payload(
        genres=[TmdbGenre(id=28, name="Action"), TmdbGenre(id=18, name="Drama")]
    )

    _apply_tmdb_update(movie, payload)

    assert movie.genres == ["Action", "Drama"]


def test_genres_keep_existing() -> None:
    movie = _make_movie(genres=["Comedy"])
    payload = _make_payload(genres=[TmdbGenre(id=28, name="Action")])

    _apply_tmdb_update(movie, payload)

    assert movie.genres == ["Comedy"]


def test_rating_value_zero_updates() -> None:
    """vote_average=0.0 is falsy but not None — should update."""
    movie = _make_movie(rating_value=5.0)
    payload = _make_payload(vote_average=0.0)

    _apply_tmdb_update(movie, payload)

    assert movie.rating_value == 0.0


def test_tmdb_metadata_fetched_at_always_set() -> None:
    movie = _make_movie(
        original_title="orig",
        overview="text",
        backdrop_path="/b.jpg",
        poster_url="http://p.jpg",
        status=MovieStatus.RELEASED,
        genres=["Action"],
        rating_value=8.5,
        rating_votes=1000,
    )
    movie.media.title = "Same"
    movie.media.release_date = datetime(2024, 1, 15, tzinfo=UTC)
    payload = _make_payload(
        title="Same",
        original_title="orig",
        overview="text",
        backdrop_path="/b.jpg",
        poster_url="http://p.jpg",
        status="Released",
        release_date=date(2024, 1, 15),
        vote_average=8.5,
        vote_count=1000,
        genres=[TmdbGenre(id=28, name="Action")],
    )

    changed = _apply_tmdb_update(movie, payload)

    assert changed is False
    assert movie.tmdb_metadata_fetched_at is not None


def test_status_overwrite() -> None:
    movie = _make_movie(status=MovieStatus.ANNOUNCED)
    payload = _make_payload(status="Released")

    _apply_tmdb_update(movie, payload)

    assert movie.status == MovieStatus.RELEASED


# --- update_movies_tmdb_metadata ---


def _mock_execute_result(movies: list) -> Mock:
    scalars_mock = Mock()
    scalars_mock.all.return_value = movies
    result_mock = Mock()
    result_mock.scalars.return_value = scalars_mock
    return result_mock


_VALID_RAW = {
    "tmdb_id": "123",
    "title": "Updated",
    "original_title": "Updated Orig",
    "overview": "desc",
    "backdrop_path": "/b.jpg",
    "poster_url": "https://img.jpg",
    "status": "Released",
    "release_date": "2024-01-15",
    "vote_average": 8.0,
    "vote_count": 500,
    "genres": [{"id": 28, "name": "Action"}],
}


@pytest.mark.asyncio
async def test_happy_path_two_movies() -> None:
    movie1 = _make_movie(tmdb_id="123")
    movie2 = _make_movie(tmdb_id="456")
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_mock_execute_result([movie1, movie2]))

    with patch(
        "app.services.update_tmdb_metadata_service.fetch_tmdb_movie",
        new_callable=AsyncMock,
        return_value=_VALID_RAW,
    ):
        result = await update_movies_tmdb_metadata(session)

    assert result.processed_count == 2
    assert result.updated_count == 2
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_skipped_on_404() -> None:
    movie = _make_movie(tmdb_id="123")
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_mock_execute_result([movie]))

    with patch(
        "app.services.update_tmdb_metadata_service.fetch_tmdb_movie",
        new_callable=AsyncMock,
        return_value=None,
    ):
        result = await update_movies_tmdb_metadata(session)

    assert result.skipped_count == 1
    assert result.updated_count == 0
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_failed_on_client_error() -> None:
    movie = _make_movie(tmdb_id="123")
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_mock_execute_result([movie]))

    with patch(
        "app.services.update_tmdb_metadata_service.fetch_tmdb_movie",
        new_callable=AsyncMock,
        side_effect=TmdbBridgeClientError(
            code=TmdbBridgeErrorCode.NETWORK_ERROR, message="unreachable"
        ),
    ):
        result = await update_movies_tmdb_metadata(session)

    assert result.failed_count == 1
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_no_movies_with_tmdb_id() -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_mock_execute_result([]))

    with patch(
        "app.services.update_tmdb_metadata_service.fetch_tmdb_movie",
        new_callable=AsyncMock,
    ) as mock_fetch:
        result = await update_movies_tmdb_metadata(session)

    assert result.processed_count == 0
    mock_fetch.assert_not_called()
    session.commit.assert_called_once()
