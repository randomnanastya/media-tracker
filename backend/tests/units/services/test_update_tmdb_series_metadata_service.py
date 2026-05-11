"""Unit tests for update_tmdb_series_metadata_service."""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.client.tmdb_bridge_client import TmdbBridgeClientError
from app.models import Season, SeriesStatus
from app.schemas.error_codes import TmdbBridgeErrorCode
from app.schemas.tmdb_bridge import (
    TmdbBridgeEpisodeResponse,
    TmdbBridgeSeasonResponse,
    TmdbBridgeSeriesResponse,
    TmdbGenre,
)
from app.services.update_tmdb_series_metadata_service import (
    _apply_episode_fields,
    _apply_season_fields,
    _apply_tmdb_series_update,
    _process_episodes,
    _process_seasons,
    update_series_tmdb_metadata,
)
from app.services.update_tmdb_series_metadata_service import (
    _apply_series_fields as _apply_series_fields_fn,
)
from tests.factories import EpisodeFactory, MediaFactory, SeasonFactory, SeriesFactory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_series(**kwargs):  # type: ignore[no-untyped-def]
    media = MediaFactory.build(title="Original Title")
    series = SeriesFactory.build(media=media, seasons=[], **kwargs)
    return series


def _make_series_payload(**kwargs) -> TmdbBridgeSeriesResponse:
    defaults: dict = {
        "tmdb_id": 12345,
        "name": "New Title",
        "original_name": "Original Name",
        "overview": "Some overview",
        "backdrop_path": "/backdrop.jpg",
        "poster_url": "https://img.tmdb.org/poster.jpg",
        "status": "Returning Series",
        "first_air_date": date(2020, 1, 1),
        "last_air_date": date(2024, 6, 1),
        "number_of_seasons": 3,
        "number_of_episodes": 30,
        "vote_average": 8.5,
        "genres": [TmdbGenre(id=18, name="Drama")],
        "seasons": [],
    }
    defaults.update(kwargs)
    return TmdbBridgeSeriesResponse(**defaults)


def _make_season_payload(**kwargs) -> TmdbBridgeSeasonResponse:
    defaults: dict = {
        "tmdb_id": 111,
        "season_number": 1,
        "overview": "Season overview",
        "poster_url": "https://img.tmdb.org/season.jpg",
        "air_date": date(2020, 1, 1),
        "vote_average": 8.0,
        "episodes": [],
    }
    defaults.update(kwargs)
    return TmdbBridgeSeasonResponse(**defaults)


def _make_episode_payload(**kwargs) -> TmdbBridgeEpisodeResponse:
    defaults: dict = {
        "tmdb_episode_id": 999,
        "episode_number": 1,
        "season_number": 1,
        "name": "Pilot",
        "overview": "Episode overview",
        "still_url": "https://img.tmdb.org/still.jpg",
        "air_date": date(2020, 1, 5),
        "episode_type": "standard",
        "vote_average": 7.5,
    }
    defaults.update(kwargs)
    return TmdbBridgeEpisodeResponse(**defaults)


def _make_season_with_episodes(**season_kwargs) -> Season:  # type: ignore[no-untyped-def]
    season = SeasonFactory.build(episodes=[], **season_kwargs)
    return season


def _mock_execute_result(series_list: list) -> Mock:
    scalars_mock = Mock()
    scalars_mock.all.return_value = series_list
    result_mock = Mock()
    result_mock.scalars.return_value = scalars_mock
    return result_mock


# ===========================================================================
# _apply_series_fields
# ===========================================================================


class TestApplySeriesFieldsOverwrite:
    def test_title_overwrite_when_different(self) -> None:
        series = _make_series()
        series.media.title = "Old Title"
        payload = _make_series_payload(name="New Title")

        changed = _apply_series_fields_fn(series, payload)

        assert changed is True
        assert series.media.title == "New Title"

    def test_title_not_changed_when_same(self) -> None:
        series = _make_series()
        series.media.title = "Same Title"
        payload = _make_series_payload(name="Same Title")

        _apply_series_fields_fn(series, payload)

        # title unchanged — but other fields may cause changed=True unless all are same
        assert series.media.title == "Same Title"

    def test_title_skipped_when_payload_name_is_none(self) -> None:
        series = _make_series()
        series.media.title = "Keep This"
        payload = _make_series_payload(name=None)

        _apply_series_fields_fn(series, payload)

        assert series.media.title == "Keep This"

    def test_status_returning_series_maps_to_continuing(self) -> None:
        series = _make_series(status=SeriesStatus.ENDED)
        payload = _make_series_payload(status="Returning Series")

        changed = _apply_series_fields_fn(series, payload)

        assert changed is True
        assert series.status == SeriesStatus.CONTINUING

    def test_status_ended_maps_correctly(self) -> None:
        series = _make_series(status=SeriesStatus.CONTINUING)
        payload = _make_series_payload(status="Ended")

        _apply_series_fields_fn(series, payload)

        assert series.status == SeriesStatus.ENDED

    def test_status_canceled_maps_correctly(self) -> None:
        series = _make_series(status=SeriesStatus.CONTINUING)
        payload = _make_series_payload(status="Canceled")

        _apply_series_fields_fn(series, payload)

        assert series.status == SeriesStatus.CANCELED

    def test_status_unknown_string_does_not_update(self) -> None:
        series = _make_series(status=SeriesStatus.CONTINUING)
        payload = _make_series_payload(status="UnknownStatus")

        _apply_series_fields_fn(series, payload)

        # map_tmdb_series_status returns None for unknown → no update
        assert series.status == SeriesStatus.CONTINUING

    def test_status_none_does_not_update(self) -> None:
        series = _make_series(status=SeriesStatus.ENDED)
        payload = _make_series_payload(status=None)

        _apply_series_fields_fn(series, payload)

        assert series.status == SeriesStatus.ENDED

    def test_rating_value_overwrite(self) -> None:
        series = _make_series(rating_value=5.0)
        payload = _make_series_payload(vote_average=9.2)

        changed = _apply_series_fields_fn(series, payload)

        assert changed is True
        assert series.rating_value == 9.2

    def test_rating_value_zero_overwrites(self) -> None:
        """vote_average=0.0 is not None — should overwrite existing."""
        series = _make_series(rating_value=7.0)
        payload = _make_series_payload(vote_average=0.0)

        _apply_series_fields_fn(series, payload)

        assert series.rating_value == 0.0

    def test_rating_value_none_does_not_update(self) -> None:
        series = _make_series(rating_value=8.0)
        payload = _make_series_payload(vote_average=None)

        _apply_series_fields_fn(series, payload)

        assert series.rating_value == 8.0

    def test_first_air_date_overwrite(self) -> None:
        series = _make_series(first_air_date=None)
        payload = _make_series_payload(first_air_date=date(2020, 3, 15))

        _apply_series_fields_fn(series, payload)

        assert series.first_air_date == datetime(2020, 3, 15, tzinfo=UTC)

    def test_first_air_date_overwrite_when_different(self) -> None:
        series = _make_series(first_air_date=datetime(2019, 1, 1, tzinfo=UTC))
        payload = _make_series_payload(first_air_date=date(2020, 3, 15))

        changed = _apply_series_fields_fn(series, payload)

        assert changed is True
        assert series.first_air_date == datetime(2020, 3, 15, tzinfo=UTC)

    def test_first_air_date_none_does_not_update(self) -> None:
        existing = datetime(2020, 1, 1, tzinfo=UTC)
        series = _make_series(first_air_date=existing)
        payload = _make_series_payload(first_air_date=None)

        _apply_series_fields_fn(series, payload)

        assert series.first_air_date == existing

    def test_last_air_date_overwrite(self) -> None:
        series = _make_series(last_air_date=None)
        payload = _make_series_payload(last_air_date=date(2024, 6, 1))

        _apply_series_fields_fn(series, payload)

        assert series.last_air_date == datetime(2024, 6, 1, tzinfo=UTC)

    def test_number_of_seasons_overwrite(self) -> None:
        series = _make_series(number_of_seasons=2)
        payload = _make_series_payload(number_of_seasons=5)

        changed = _apply_series_fields_fn(series, payload)

        assert changed is True
        assert series.number_of_seasons == 5

    def test_number_of_seasons_none_does_not_update(self) -> None:
        series = _make_series(number_of_seasons=3)
        payload = _make_series_payload(number_of_seasons=None)

        _apply_series_fields_fn(series, payload)

        assert series.number_of_seasons == 3

    def test_number_of_episodes_overwrite(self) -> None:
        series = _make_series(number_of_episodes=10)
        payload = _make_series_payload(number_of_episodes=25)

        changed = _apply_series_fields_fn(series, payload)

        assert changed is True
        assert series.number_of_episodes == 25

    def test_number_of_episodes_none_does_not_update(self) -> None:
        series = _make_series(number_of_episodes=10)
        payload = _make_series_payload(number_of_episodes=None)

        _apply_series_fields_fn(series, payload)

        assert series.number_of_episodes == 10


class TestApplySeriesFieldsFillIfEmpty:
    def test_original_name_filled_when_empty(self) -> None:
        series = _make_series(original_name=None)
        payload = _make_series_payload(original_name="Orig Name")

        _apply_series_fields_fn(series, payload)

        assert series.original_name == "Orig Name"

    def test_original_name_not_overwritten_when_set(self) -> None:
        series = _make_series(original_name="Already Set")
        payload = _make_series_payload(original_name="Different")

        _apply_series_fields_fn(series, payload)

        assert series.original_name == "Already Set"

    def test_overview_filled_when_empty(self) -> None:
        series = _make_series(overview=None)
        payload = _make_series_payload(overview="New overview")

        _apply_series_fields_fn(series, payload)

        assert series.overview == "New overview"

    def test_overview_not_overwritten_when_set(self) -> None:
        series = _make_series(overview="Existing overview")
        payload = _make_series_payload(overview="New overview")

        _apply_series_fields_fn(series, payload)

        assert series.overview == "Existing overview"

    def test_backdrop_path_filled_when_empty(self) -> None:
        series = _make_series(backdrop_path=None)
        payload = _make_series_payload(backdrop_path="/new_backdrop.jpg")

        _apply_series_fields_fn(series, payload)

        assert series.backdrop_path == "/new_backdrop.jpg"

    def test_backdrop_path_not_overwritten_when_set(self) -> None:
        series = _make_series(backdrop_path="/existing.jpg")
        payload = _make_series_payload(backdrop_path="/new.jpg")

        _apply_series_fields_fn(series, payload)

        assert series.backdrop_path == "/existing.jpg"

    def test_poster_url_filled_when_empty(self) -> None:
        series = _make_series(poster_url=None)
        payload = _make_series_payload(poster_url="https://new-poster.jpg")

        _apply_series_fields_fn(series, payload)

        assert series.poster_url == "https://new-poster.jpg"

    def test_poster_url_not_overwritten_when_set(self) -> None:
        series = _make_series(poster_url="https://existing.jpg")
        payload = _make_series_payload(poster_url="https://new.jpg")

        _apply_series_fields_fn(series, payload)

        assert series.poster_url == "https://existing.jpg"

    def test_genres_filled_when_empty(self) -> None:
        series = _make_series(genres=None)
        payload = _make_series_payload(
            genres=[TmdbGenre(id=18, name="Drama"), TmdbGenre(id=28, name="Action")]
        )

        _apply_series_fields_fn(series, payload)

        assert series.genres == ["Drama", "Action"]

    def test_genres_not_overwritten_when_set(self) -> None:
        series = _make_series(genres=["Comedy"])
        payload = _make_series_payload(genres=[TmdbGenre(id=18, name="Drama")])

        _apply_series_fields_fn(series, payload)

        assert series.genres == ["Comedy"]

    def test_genres_not_set_when_payload_empty_list(self) -> None:
        series = _make_series(genres=None)
        payload = _make_series_payload(genres=[])

        _apply_series_fields_fn(series, payload)

        assert series.genres is None


class TestApplySeriesFieldsReturnValue:
    def test_returns_true_when_title_changed(self) -> None:
        series = _make_series()
        series.media.title = "Old"
        payload = _make_series_payload(
            name="New",
            original_name=series.original_name,
            overview=series.overview,
            backdrop_path=series.backdrop_path,
            poster_url=series.poster_url,
            genres=[],
            status=None,
            first_air_date=None,
            last_air_date=None,
            number_of_seasons=series.number_of_seasons,
            number_of_episodes=series.number_of_episodes,
            vote_average=series.rating_value,
        )

        result = _apply_series_fields_fn(series, payload)

        assert result is True

    def test_returns_false_when_nothing_changed(self) -> None:
        series = _make_series(
            original_name=None,
            overview=None,
            backdrop_path=None,
            poster_url=None,
            genres=None,
            status=None,
            first_air_date=None,
            last_air_date=None,
            number_of_seasons=None,
            number_of_episodes=None,
            rating_value=None,
        )
        series.media.title = "Same"
        payload = _make_series_payload(
            name="Same",
            original_name=None,
            overview=None,
            backdrop_path=None,
            poster_url=None,
            genres=[],
            status=None,
            first_air_date=None,
            last_air_date=None,
            number_of_seasons=None,
            number_of_episodes=None,
            vote_average=None,
        )

        result = _apply_series_fields_fn(series, payload)

        assert result is False


# ===========================================================================
# _apply_season_fields
# ===========================================================================


class TestApplySeasonFieldsFillIfEmpty:
    # tmdb_id is handled in _process_seasons (with savepoint), not here

    def test_overview_filled_when_empty(self) -> None:
        season = SeasonFactory.build(tmdb_id=1, overview=None)
        payload = _make_season_payload(overview="Season story")

        _apply_season_fields(season, payload)

        assert season.overview == "Season story"

    def test_overview_not_overwritten_when_set(self) -> None:
        season = SeasonFactory.build(tmdb_id=1, overview="Existing overview")
        payload = _make_season_payload(overview="New overview")

        _apply_season_fields(season, payload)

        assert season.overview == "Existing overview"

    def test_poster_url_filled_when_empty(self) -> None:
        season = SeasonFactory.build(tmdb_id=1, poster_url=None)
        payload = _make_season_payload(poster_url="https://poster.jpg")

        _apply_season_fields(season, payload)

        assert season.poster_url == "https://poster.jpg"

    def test_poster_url_not_overwritten_when_set(self) -> None:
        season = SeasonFactory.build(tmdb_id=1, poster_url="https://existing.jpg")
        payload = _make_season_payload(poster_url="https://new.jpg")

        _apply_season_fields(season, payload)

        assert season.poster_url == "https://existing.jpg"


class TestApplySeasonFieldsOverwrite:
    def test_release_date_overwrite_from_air_date(self) -> None:
        season = SeasonFactory.build(
            release_date=None, tmdb_id=None, overview=None, poster_url=None
        )
        payload = _make_season_payload(air_date=date(2021, 5, 10))

        changed = _apply_season_fields(season, payload)

        assert changed is True
        assert season.release_date == datetime(2021, 5, 10, tzinfo=UTC)

    def test_release_date_overwrites_existing(self) -> None:
        season = SeasonFactory.build(
            release_date=datetime(2019, 1, 1, tzinfo=UTC),
            tmdb_id=None,
            overview=None,
            poster_url=None,
        )
        payload = _make_season_payload(air_date=date(2021, 5, 10))

        changed = _apply_season_fields(season, payload)

        assert changed is True
        assert season.release_date == datetime(2021, 5, 10, tzinfo=UTC)

    def test_release_date_not_updated_when_air_date_none(self) -> None:
        existing = datetime(2020, 1, 1, tzinfo=UTC)
        season = SeasonFactory.build(release_date=existing, tmdb_id=1, vote_average=8.0)
        payload = _make_season_payload(
            air_date=None, vote_average=8.0, overview=None, poster_url=None
        )

        _apply_season_fields(season, payload)

        assert season.release_date == existing

    def test_vote_average_overwrite(self) -> None:
        season = SeasonFactory.build(
            vote_average=5.0, tmdb_id=1, overview=None, poster_url=None, release_date=None
        )
        payload = _make_season_payload(vote_average=9.0, air_date=None)

        changed = _apply_season_fields(season, payload)

        assert changed is True
        assert season.vote_average == 9.0

    def test_vote_average_not_updated_when_same(self) -> None:
        season = SeasonFactory.build(vote_average=8.0, tmdb_id=1, overview="x", poster_url="x")
        payload = _make_season_payload(
            vote_average=8.0, air_date=None, overview="x", poster_url="x"
        )

        changed = _apply_season_fields(season, payload)

        assert changed is False

    def test_vote_average_none_does_not_update(self) -> None:
        season = SeasonFactory.build(vote_average=7.5, tmdb_id=1)
        payload = _make_season_payload(vote_average=None, air_date=None)

        _apply_season_fields(season, payload)

        assert season.vote_average == 7.5


# ===========================================================================
# _apply_episode_fields
# ===========================================================================


class TestApplyEpisodeFieldsFillIfEmpty:
    def test_tmdb_id_filled_when_none(self) -> None:
        ep = EpisodeFactory.build(tmdb_id=None)
        payload = _make_episode_payload(tmdb_episode_id=42)

        changed = _apply_episode_fields(ep, payload)

        assert changed is True
        assert ep.tmdb_id == 42

    def test_tmdb_id_not_overwritten_when_set(self) -> None:
        ep = EpisodeFactory.build(tmdb_id=10)
        payload = _make_episode_payload(tmdb_episode_id=99)

        _apply_episode_fields(ep, payload)

        assert ep.tmdb_id == 10

    def test_title_filled_when_empty(self) -> None:
        ep = EpisodeFactory.build(title="", tmdb_id=1)
        payload = _make_episode_payload(name="New Episode Name")

        _apply_episode_fields(ep, payload)

        assert ep.title == "New Episode Name"

    def test_title_not_overwritten_when_set(self) -> None:
        ep = EpisodeFactory.build(title="Existing Title", tmdb_id=1)
        payload = _make_episode_payload(name="Different Name")

        _apply_episode_fields(ep, payload)

        assert ep.title == "Existing Title"

    def test_title_skipped_when_payload_name_none(self) -> None:
        ep = EpisodeFactory.build(title="", tmdb_id=1)
        payload = _make_episode_payload(name=None)

        _apply_episode_fields(ep, payload)

        assert ep.title == ""

    def test_overview_filled_when_empty(self) -> None:
        ep = EpisodeFactory.build(overview=None, tmdb_id=1)
        payload = _make_episode_payload(overview="Plot summary")

        _apply_episode_fields(ep, payload)

        assert ep.overview == "Plot summary"

    def test_overview_not_overwritten_when_set(self) -> None:
        ep = EpisodeFactory.build(overview="Existing", tmdb_id=1)
        payload = _make_episode_payload(overview="New")

        _apply_episode_fields(ep, payload)

        assert ep.overview == "Existing"

    def test_episode_type_filled_when_empty(self) -> None:
        ep = EpisodeFactory.build(episode_type=None, tmdb_id=1)
        payload = _make_episode_payload(episode_type="finale")

        _apply_episode_fields(ep, payload)

        assert ep.episode_type == "finale"

    def test_episode_type_not_overwritten_when_set(self) -> None:
        ep = EpisodeFactory.build(episode_type="standard", tmdb_id=1)
        payload = _make_episode_payload(episode_type="finale")

        _apply_episode_fields(ep, payload)

        assert ep.episode_type == "standard"

    def test_still_url_filled_when_empty(self) -> None:
        ep = EpisodeFactory.build(still_url=None, tmdb_id=1)
        payload = _make_episode_payload(still_url="https://still.jpg")

        _apply_episode_fields(ep, payload)

        assert ep.still_url == "https://still.jpg"

    def test_still_url_not_overwritten_when_set(self) -> None:
        ep = EpisodeFactory.build(still_url="https://existing.jpg", tmdb_id=1)
        payload = _make_episode_payload(still_url="https://new.jpg")

        _apply_episode_fields(ep, payload)

        assert ep.still_url == "https://existing.jpg"


class TestApplyEpisodeFieldsOverwrite:
    def test_air_date_overwrite(self) -> None:
        ep = EpisodeFactory.build(air_date=None, tmdb_id=1)
        payload = _make_episode_payload(air_date=date(2021, 3, 7))

        changed = _apply_episode_fields(ep, payload)

        assert changed is True
        assert ep.air_date == datetime(2021, 3, 7, tzinfo=UTC)

    def test_air_date_overwrites_existing(self) -> None:
        ep = EpisodeFactory.build(air_date=datetime(2019, 1, 1, tzinfo=UTC), tmdb_id=1)
        payload = _make_episode_payload(air_date=date(2021, 3, 7))

        changed = _apply_episode_fields(ep, payload)

        assert changed is True
        assert ep.air_date == datetime(2021, 3, 7, tzinfo=UTC)

    def test_air_date_none_does_not_update(self) -> None:
        existing = datetime(2020, 1, 1, tzinfo=UTC)
        ep = EpisodeFactory.build(air_date=existing, tmdb_id=1)
        payload = _make_episode_payload(air_date=None)

        _apply_episode_fields(ep, payload)

        assert ep.air_date == existing

    def test_vote_average_greater_than_zero_overwrites(self) -> None:
        ep = EpisodeFactory.build(vote_average=5.0, tmdb_id=1)
        payload = _make_episode_payload(vote_average=9.0)

        changed = _apply_episode_fields(ep, payload)

        assert changed is True
        assert ep.vote_average == 9.0

    def test_vote_average_zero_not_written(self) -> None:
        """vote_average == 0.0 must NOT be saved."""
        ep = EpisodeFactory.build(vote_average=7.0, tmdb_id=1)
        payload = _make_episode_payload(vote_average=0.0)

        _apply_episode_fields(ep, payload)

        assert ep.vote_average == 7.0

    def test_vote_average_none_not_written(self) -> None:
        ep = EpisodeFactory.build(vote_average=7.0, tmdb_id=1)
        payload = _make_episode_payload(vote_average=None)

        _apply_episode_fields(ep, payload)

        assert ep.vote_average == 7.0

    def test_vote_average_positive_updates_when_same_value_no_change(self) -> None:
        ep = EpisodeFactory.build(vote_average=8.0, tmdb_id=1)
        # air_date same so no change from that; title, overview, episode_type, still_url all set
        payload = _make_episode_payload(
            vote_average=8.0,
            air_date=None,
            name=None,
            overview=None,
            episode_type=None,
            still_url=None,
            tmdb_episode_id=None,
        )

        changed = _apply_episode_fields(ep, payload)

        assert changed is False


# ===========================================================================
# _process_episodes
# ===========================================================================


class TestProcessEpisodes:
    def test_new_episode_created_when_absent(self) -> None:
        season = _make_season_with_episodes(id=10)
        payload = _make_episode_payload(episode_number=5)

        changed = _process_episodes(season, [payload])

        assert changed is True
        assert len(season.episodes) == 1
        assert season.episodes[0].number == 5

    def test_new_episode_title_from_name(self) -> None:
        season = _make_season_with_episodes(id=10)
        payload = _make_episode_payload(episode_number=1, name="Great Pilot")

        _process_episodes(season, [payload])

        assert season.episodes[0].title == "Great Pilot"

    def test_new_episode_fallback_title_when_name_none(self) -> None:
        season = _make_season_with_episodes(id=10)
        payload = _make_episode_payload(episode_number=7, name=None)

        _process_episodes(season, [payload])

        assert season.episodes[0].title == "Episode 7"

    def test_new_episode_fallback_title_when_name_empty(self) -> None:
        """Empty string is falsy — should use fallback title."""
        season = _make_season_with_episodes(id=10)
        payload = _make_episode_payload(episode_number=3, name="")

        _process_episodes(season, [payload])

        assert season.episodes[0].title == "Episode 3"

    def test_new_episode_vote_average_zero_stored_as_none(self) -> None:
        """vote_average=0.0 on new episode → None (not recorded)."""
        season = _make_season_with_episodes(id=10)
        payload = _make_episode_payload(episode_number=1, vote_average=0.0)

        _process_episodes(season, [payload])

        assert season.episodes[0].vote_average is None

    def test_new_episode_vote_average_positive_stored(self) -> None:
        season = _make_season_with_episodes(id=10)
        payload = _make_episode_payload(episode_number=1, vote_average=8.1)

        _process_episodes(season, [payload])

        assert season.episodes[0].vote_average == 8.1

    def test_existing_episode_matched_by_number(self) -> None:
        ep = EpisodeFactory.build(number=2, title="Old Title", tmdb_id=None)
        season = _make_season_with_episodes(id=10)
        season.episodes = [ep]
        payload = _make_episode_payload(episode_number=2, name="Old Title", tmdb_episode_id=77)

        _process_episodes(season, [payload])

        assert len(season.episodes) == 1
        assert season.episodes[0].tmdb_id == 77

    def test_episode_in_db_without_payload_not_deleted(self) -> None:
        ep_old = EpisodeFactory.build(number=1, title="Old Ep")
        season = _make_season_with_episodes(id=10)
        season.episodes = [ep_old]
        payload = _make_episode_payload(episode_number=2)

        _process_episodes(season, [payload])

        assert any(e.number == 1 for e in season.episodes)

    def test_returns_false_when_no_changes_to_existing_episode(self) -> None:
        ep = EpisodeFactory.build(
            number=1,
            tmdb_id=10,
            title="Title",
            overview="Ov",
            episode_type="standard",
            still_url="http://s.jpg",
            air_date=datetime(2021, 3, 7, tzinfo=UTC),
            vote_average=8.0,
        )
        season = _make_season_with_episodes(id=10)
        season.episodes = [ep]

        payload = _make_episode_payload(
            episode_number=1,
            tmdb_episode_id=10,
            name=None,
            overview=None,
            still_url=None,
            air_date=None,
            episode_type=None,
            vote_average=None,
        )

        changed = _process_episodes(season, [payload])

        assert changed is False

    def test_new_episode_air_date_converted(self) -> None:
        season = _make_season_with_episodes(id=10)
        payload = _make_episode_payload(episode_number=1, air_date=date(2022, 8, 15))

        _process_episodes(season, [payload])

        assert season.episodes[0].air_date == datetime(2022, 8, 15, tzinfo=UTC)


# ===========================================================================
# _process_seasons
# ===========================================================================


class TestProcessSeasons:
    @pytest.mark.asyncio
    async def test_new_season_created_when_absent(self) -> None:
        series = _make_series()
        series.id = 5
        series.seasons = []
        session = AsyncMock()
        session.add = Mock()
        session.flush = AsyncMock()

        payload = _make_series_payload(
            seasons=[_make_season_payload(season_number=1, tmdb_id=None, episodes=[])]
        )

        changed = await _process_seasons(series, payload.seasons, session)

        assert changed is True
        session.add.assert_called_once()
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_new_season_has_correct_series_id_and_number(self) -> None:
        series = _make_series()
        series.id = 42
        series.seasons = []
        session = AsyncMock()
        session.add = Mock()
        session.flush = AsyncMock()

        season_payload = _make_season_payload(season_number=3, episodes=[])
        await _process_seasons(series, [season_payload], session)

        created_season: Season = session.add.call_args[0][0]
        assert created_season.series_id == 42
        assert created_season.number == 3

    @pytest.mark.asyncio
    async def test_existing_season_matched_by_number(self) -> None:
        existing_season = SeasonFactory.build(
            number=2, tmdb_id=None, overview=None, poster_url=None
        )
        existing_season.episodes = []
        series = _make_series()
        series.seasons = [existing_season]
        session = AsyncMock()
        session.add = Mock()
        session.flush = AsyncMock()

        season_payload = _make_season_payload(season_number=2, tmdb_id=777, episodes=[])
        await _process_seasons(series, [season_payload], session)

        session.add.assert_not_called()
        assert existing_season.tmdb_id == 777

    @pytest.mark.asyncio
    async def test_season_in_db_without_payload_not_deleted(self) -> None:
        extra_season = SeasonFactory.build(number=99)
        extra_season.episodes = []
        series = _make_series()
        series.seasons = [extra_season]
        session = AsyncMock()
        session.add = Mock()
        session.flush = AsyncMock()

        # payload has season_number=1 only — season 99 should survive
        await _process_seasons(
            series, [_make_season_payload(season_number=1, episodes=[])], session
        )

        assert any(s.number == 99 for s in series.seasons)

    @pytest.mark.asyncio
    async def test_multiple_new_seasons_all_flushed(self) -> None:
        series = _make_series()
        series.id = 1
        series.seasons = []
        session = AsyncMock()
        session.add = Mock()
        session.flush = AsyncMock()

        payloads = [
            _make_season_payload(season_number=1, tmdb_id=None, episodes=[]),
            _make_season_payload(season_number=2, tmdb_id=None, episodes=[]),
        ]
        await _process_seasons(series, payloads, session)

        assert session.add.call_count == 2
        assert session.flush.call_count == 2


# ===========================================================================
# _apply_tmdb_series_update
# ===========================================================================


class TestApplyTmdbSeriesUpdate:
    @pytest.mark.asyncio
    async def test_tmdb_metadata_fetched_at_always_set(self) -> None:
        series = _make_series(
            original_name=None,
            overview=None,
            backdrop_path=None,
            poster_url=None,
            genres=None,
            status=None,
            first_air_date=None,
            last_air_date=None,
            number_of_seasons=None,
            number_of_episodes=None,
            rating_value=None,
            tmdb_metadata_fetched_at=None,
        )
        series.media.title = "Same"
        series.seasons = []
        session = AsyncMock()
        session.add = Mock()
        session.flush = AsyncMock()

        payload = _make_series_payload(
            name="Same",
            original_name=None,
            overview=None,
            backdrop_path=None,
            poster_url=None,
            genres=[],
            status=None,
            first_air_date=None,
            last_air_date=None,
            number_of_seasons=None,
            number_of_episodes=None,
            vote_average=None,
            seasons=[],
        )

        await _apply_tmdb_series_update(series, payload, session)

        assert series.tmdb_metadata_fetched_at is not None
        assert series.tmdb_metadata_fetched_at.tzinfo is not None

    @pytest.mark.asyncio
    async def test_returns_true_when_fields_changed(self) -> None:
        series = _make_series(
            original_name=None,
            overview=None,
            backdrop_path=None,
            poster_url=None,
            genres=None,
            status=None,
            first_air_date=None,
            last_air_date=None,
            number_of_seasons=None,
            number_of_episodes=None,
            rating_value=None,
        )
        series.media.title = "Old"
        series.seasons = []
        session = AsyncMock()
        session.add = Mock()
        session.flush = AsyncMock()

        payload = _make_series_payload(name="New", seasons=[])

        result = await _apply_tmdb_series_update(series, payload, session)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_nothing_changed_no_new_seasons(self) -> None:
        series = _make_series(
            original_name=None,
            overview=None,
            backdrop_path=None,
            poster_url=None,
            genres=None,
            status=None,
            first_air_date=None,
            last_air_date=None,
            number_of_seasons=None,
            number_of_episodes=None,
            rating_value=None,
        )
        series.media.title = "Same"
        series.seasons = []
        session = AsyncMock()
        session.add = Mock()
        session.flush = AsyncMock()

        payload = _make_series_payload(
            name="Same",
            original_name=None,
            overview=None,
            backdrop_path=None,
            poster_url=None,
            genres=[],
            status=None,
            first_air_date=None,
            last_air_date=None,
            number_of_seasons=None,
            number_of_episodes=None,
            vote_average=None,
            seasons=[],
        )

        result = await _apply_tmdb_series_update(series, payload, session)

        assert result is False

    @pytest.mark.asyncio
    async def test_new_season_in_payload_marks_changed(self) -> None:
        series = _make_series(
            original_name=None,
            overview=None,
            backdrop_path=None,
            poster_url=None,
            genres=None,
            status=None,
            first_air_date=None,
            last_air_date=None,
            number_of_seasons=None,
            number_of_episodes=None,
            rating_value=None,
        )
        series.media.title = "Same"
        series.seasons = []
        series.id = 1
        session = AsyncMock()
        session.add = Mock()
        session.flush = AsyncMock()

        payload = _make_series_payload(
            name="Same",
            original_name=None,
            overview=None,
            backdrop_path=None,
            poster_url=None,
            genres=[],
            status=None,
            first_air_date=None,
            last_air_date=None,
            number_of_seasons=None,
            number_of_episodes=None,
            vote_average=None,
            seasons=[_make_season_payload(season_number=1, episodes=[])],
        )

        result = await _apply_tmdb_series_update(series, payload, session)

        assert result is True


# ===========================================================================
# update_series_tmdb_metadata (top-level, integration-light)
# ===========================================================================


_VALID_SERIES_RAW = {
    "tmdb_id": 12345,
    "name": "Updated Series",
    "original_name": "Updated Orig",
    "overview": "desc",
    "backdrop_path": "/b.jpg",
    "poster_url": "https://img.jpg",
    "status": "Returning Series",
    "first_air_date": "2020-01-01",
    "last_air_date": "2024-06-01",
    "number_of_seasons": 3,
    "number_of_episodes": 30,
    "vote_average": 8.0,
    "genres": [{"id": 18, "name": "Drama"}],
    "seasons": [],
}


@pytest.mark.asyncio
async def test_update_series_happy_path_two_series() -> None:
    series1 = _make_series(tmdb_id="12345", original_name=None, overview=None)
    series1.seasons = []
    series2 = _make_series(tmdb_id="67890", original_name=None, overview=None)
    series2.seasons = []

    session = AsyncMock()
    session.execute = AsyncMock(return_value=_mock_execute_result([series1, series2]))
    session.add = Mock()
    session.flush = AsyncMock()

    with patch(
        "app.services.update_tmdb_series_metadata_service.fetch_tmdb_series",
        new_callable=AsyncMock,
        return_value=_VALID_SERIES_RAW,
    ):
        result = await update_series_tmdb_metadata(session)

    assert result.processed_count == 2
    assert result.updated_count == 2
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_series_skipped_on_none_response() -> None:
    series = _make_series(tmdb_id="12345")
    series.seasons = []
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_mock_execute_result([series]))

    with patch(
        "app.services.update_tmdb_series_metadata_service.fetch_tmdb_series",
        new_callable=AsyncMock,
        return_value=None,
    ):
        result = await update_series_tmdb_metadata(session)

    assert result.skipped_count == 1
    assert result.updated_count == 0
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_series_failed_on_client_error() -> None:
    series = _make_series(tmdb_id="12345")
    series.seasons = []
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_mock_execute_result([series]))

    with patch(
        "app.services.update_tmdb_series_metadata_service.fetch_tmdb_series",
        new_callable=AsyncMock,
        side_effect=TmdbBridgeClientError(
            code=TmdbBridgeErrorCode.NETWORK_ERROR, message="unreachable"
        ),
    ):
        result = await update_series_tmdb_metadata(session)

    assert result.failed_count == 1
    assert result.updated_count == 0
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_series_failed_on_invalid_payload() -> None:
    series = _make_series(tmdb_id="12345")
    series.seasons = []
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_mock_execute_result([series]))

    with patch(
        "app.services.update_tmdb_series_metadata_service.fetch_tmdb_series",
        new_callable=AsyncMock,
        return_value={"bad_field": "no tmdb_id here"},
    ):
        result = await update_series_tmdb_metadata(session)

    assert result.failed_count == 1
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_series_no_series_to_process() -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_mock_execute_result([]))

    with patch(
        "app.services.update_tmdb_series_metadata_service.fetch_tmdb_series",
        new_callable=AsyncMock,
    ) as mock_fetch:
        result = await update_series_tmdb_metadata(session)

    assert result.processed_count == 0
    mock_fetch.assert_not_called()
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_series_commit_failure_raises() -> None:
    series = _make_series(tmdb_id="12345", original_name=None, overview=None)
    series.seasons = []
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_mock_execute_result([series]))
    session.commit = AsyncMock(side_effect=RuntimeError("DB gone"))
    session.rollback = AsyncMock()

    with (
        patch(
            "app.services.update_tmdb_series_metadata_service.fetch_tmdb_series",
            new_callable=AsyncMock,
            return_value=_VALID_SERIES_RAW,
        ),
        pytest.raises(RuntimeError, match="DB gone"),
    ):
        await update_series_tmdb_metadata(session)

    session.rollback.assert_called_once()
