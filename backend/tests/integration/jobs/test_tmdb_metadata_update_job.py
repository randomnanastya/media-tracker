"""Integration tests for TMDB metadata update job.

Tests use a real PostgreSQL test DB (via session_no_expire) and intercept
HTTP calls to the bridge with pytest-httpx.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.media import Episode, MediaType, Movie, Season, Series, SeriesStatus
from app.models.schedule import SchedulePreset, SyncJobType, SyncSchedule
from app.services.update_tmdb_metadata_service import update_tmdb_metadata
from app.services.update_tmdb_series_metadata_service import update_series_tmdb_metadata
from tests.factories import MediaFactory, MovieFactory, SeriesFactory, SyncScheduleFactory

BRIDGE_BASE = "https://bridge.mediatrackr.org"


# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------


def _series_payload(tmdb_id: int, seasons: list[dict]) -> dict:
    return {
        "tmdb_id": tmdb_id,
        "name": "Test Series",
        "status": "Returning Series",
        "vote_average": 8.5,
        "genres": [{"id": 1, "name": "Drama"}],
        "seasons": seasons,
    }


def _season_payload(season_number: int, tmdb_id: int, episodes: list[dict]) -> dict:
    return {
        "season_number": season_number,
        "tmdb_id": tmdb_id,
        "air_date": "2023-01-15",
        "vote_average": 8.0,
        "episodes": episodes,
    }


def _episode_payload(episode_number: int, season_number: int, name: str) -> dict:
    return {
        "episode_number": episode_number,
        "season_number": season_number,
        "name": name,
        "air_date": "2023-01-15",
        "vote_average": 8.5,
    }


def _movie_payload(tmdb_id: str) -> dict:
    return {
        "tmdb_id": tmdb_id,
        "title": "Test Movie Updated",
        "status": "Released",
        "vote_average": 7.9,
        "vote_count": 1500,
        "genres": [{"id": 28, "name": "Action"}],
        "release_date": "2022-06-10",
        "overview": "A movie overview.",
        "poster_url": "https://img.tmdb.org/poster.jpg",
    }


# ---------------------------------------------------------------------------
# Helpers: DB object creation
# ---------------------------------------------------------------------------


async def _create_series(session: AsyncSession, tmdb_id: str, title: str = "My Series") -> Series:
    media = MediaFactory.build(media_type=MediaType.SERIES, title=title)
    session.add(media)
    await session.flush()

    series = SeriesFactory.build(
        id=media.id,
        tmdb_id=tmdb_id,
        sonarr_id=None,
        tvdb_id=None,
        imdb_id=None,
        jellyfin_id=None,
        original_name=None,
        overview=None,
        backdrop_path=None,
        poster_url=None,
        genres=None,
        rating_value=None,
        status=None,
        first_air_date=None,
        last_air_date=None,
        number_of_seasons=None,
        number_of_episodes=None,
        tmdb_metadata_fetched_at=None,
        media=media,
    )
    session.add(series)
    await session.flush()
    return series


async def _create_movie(session: AsyncSession, tmdb_id: str, title: str = "My Movie") -> Movie:
    media = MediaFactory.build(media_type=MediaType.MOVIE, title=title)
    session.add(media)
    await session.flush()

    movie = MovieFactory.build(
        id=media.id,
        tmdb_id=tmdb_id,
        radarr_id=None,
        imdb_id=None,
        jellyfin_id=None,
        original_title=None,
        overview=None,
        backdrop_path=None,
        poster_url=None,
        genres=None,
        rating_value=None,
        rating_votes=None,
        status=None,
        tmdb_metadata_fetched_at=None,
        media=media,
    )
    session.add(movie)
    await session.flush()
    return movie


# ===========================================================================
# Test 1: seasons and episodes are created from bridge response
# ===========================================================================


async def test_seasons_and_episodes_created_from_bridge(
    session_no_expire: AsyncSession,
    httpx_mock,
) -> None:
    """Bridge returns 1 season with 2 episodes → DB gets Season + 2 Episodes."""
    series = await _create_series(session_no_expire, tmdb_id="1234")
    await session_no_expire.commit()

    payload = _series_payload(
        tmdb_id=1234,
        seasons=[
            _season_payload(
                season_number=1,
                tmdb_id=101,
                episodes=[
                    _episode_payload(1, 1, "Pilot"),
                    _episode_payload(2, 1, "Episode 2"),
                ],
            )
        ],
    )
    httpx_mock.add_response(
        url=f"{BRIDGE_BASE}/tmdb/tv/{series.tmdb_id}",
        json=payload,
        status_code=200,
    )

    result = await update_series_tmdb_metadata(session_no_expire)

    assert result.processed_count == 1
    assert result.updated_count == 1

    # Verify DB state
    seasons = list(
        (await session_no_expire.execute(select(Season).where(Season.series_id == series.id)))
        .scalars()
        .all()
    )
    assert len(seasons) == 1
    season_db = seasons[0]
    assert season_db.number == 1
    assert season_db.tmdb_id == 101

    episodes = list(
        (
            await session_no_expire.execute(
                select(Episode).where(Episode.season_id == season_db.id).order_by(Episode.number)
            )
        )
        .scalars()
        .all()
    )
    assert len(episodes) == 2
    assert episodes[0].number == 1
    assert episodes[0].title == "Pilot"
    assert episodes[1].number == 2
    assert episodes[1].title == "Episode 2"


async def test_two_seasons_with_two_episodes_each_created(
    session_no_expire: AsyncSession,
    httpx_mock,
) -> None:
    """Bridge returns 2 seasons × 2 episodes each → 2 Season + 4 Episode rows in DB."""
    series = await _create_series(session_no_expire, tmdb_id="5678")
    await session_no_expire.commit()

    payload = _series_payload(
        tmdb_id=5678,
        seasons=[
            _season_payload(
                1,
                201,
                [_episode_payload(1, 1, "S1E1"), _episode_payload(2, 1, "S1E2")],
            ),
            _season_payload(
                2,
                202,
                [_episode_payload(1, 2, "S2E1"), _episode_payload(2, 2, "S2E2")],
            ),
        ],
    )
    httpx_mock.add_response(
        url=f"{BRIDGE_BASE}/tmdb/tv/{series.tmdb_id}",
        json=payload,
        status_code=200,
    )

    result = await update_series_tmdb_metadata(session_no_expire)

    assert result.processed_count == 1
    assert result.updated_count == 1

    seasons = list(
        (
            await session_no_expire.execute(
                select(Season).where(Season.series_id == series.id).order_by(Season.number)
            )
        )
        .scalars()
        .all()
    )
    assert len(seasons) == 2
    assert seasons[0].number == 1
    assert seasons[1].number == 2

    for season_db in seasons:
        episodes = list(
            (
                await session_no_expire.execute(
                    select(Episode)
                    .where(Episode.season_id == season_db.id)
                    .order_by(Episode.number)
                )
            )
            .scalars()
            .all()
        )
        assert len(episodes) == 2


# ===========================================================================
# Test 2: idempotency — second call with same data → updated_count == 0
# ===========================================================================


async def test_idempotency_second_call_returns_zero_updated(
    session_no_expire: AsyncSession,
    httpx_mock,
) -> None:
    """Running the job twice with the same bridge data does not re-update anything."""
    series = await _create_series(session_no_expire, tmdb_id="9999")
    await session_no_expire.commit()

    payload = _series_payload(
        tmdb_id=9999,
        seasons=[
            _season_payload(
                1,
                301,
                [_episode_payload(1, 1, "Pilot")],
            )
        ],
    )

    # First call — adds season + episode, marks changed
    httpx_mock.add_response(
        url=f"{BRIDGE_BASE}/tmdb/tv/{series.tmdb_id}",
        json=payload,
        status_code=200,
    )
    first_result = await update_series_tmdb_metadata(session_no_expire)
    assert first_result.updated_count == 1

    # Simulate fresh-session behavior: in production each job run gets a new session,
    # so selectinload always re-fetches seasons. Here we expire the stale collection manually.
    session_no_expire.expire(series, attribute_names=["seasons"])

    # Second call — same payload, nothing new
    httpx_mock.add_response(
        url=f"{BRIDGE_BASE}/tmdb/tv/{series.tmdb_id}",
        json=payload,
        status_code=200,
    )
    second_result = await update_series_tmdb_metadata(session_no_expire)

    assert second_result.updated_count == 0
    assert second_result.processed_count == 1

    # No duplicate seasons or episodes
    seasons = list(
        (await session_no_expire.execute(select(Season).where(Season.series_id == series.id)))
        .scalars()
        .all()
    )
    assert len(seasons) == 1

    episodes = list(
        (await session_no_expire.execute(select(Episode).where(Episode.season_id == seasons[0].id)))
        .scalars()
        .all()
    )
    assert len(episodes) == 1


# ===========================================================================
# Test 3: orchestrator update_tmdb_metadata processes both movies and series
# ===========================================================================


async def test_orchestrator_processes_both_movie_and_series(
    session_no_expire: AsyncSession,
    httpx_mock,
) -> None:
    """update_tmdb_metadata() runs movie + series jobs; total processed_count == 2."""
    movie = await _create_movie(session_no_expire, tmdb_id="7777")
    series = await _create_series(session_no_expire, tmdb_id="8888")
    await session_no_expire.commit()

    movie_payload = _movie_payload(tmdb_id="7777")
    series_payload = _series_payload(tmdb_id=8888, seasons=[])

    httpx_mock.add_response(
        url=f"{BRIDGE_BASE}/tmdb/movie/{movie.tmdb_id}",
        json=movie_payload,
        status_code=200,
    )
    httpx_mock.add_response(
        url=f"{BRIDGE_BASE}/tmdb/tv/{series.tmdb_id}",
        json=series_payload,
        status_code=200,
    )

    result = await update_tmdb_metadata(session_no_expire)

    # Both movie and series were processed
    assert result.processed_count == 2
    # Both had fields to update (new data)
    assert result.updated_count == 2


async def test_orchestrator_counts_are_sum_of_both_jobs(
    session_no_expire: AsyncSession,
    httpx_mock,
) -> None:
    """Counters in orchestrator result equal sum from movie job + series job."""
    movie = await _create_movie(session_no_expire, tmdb_id="1001")
    series = await _create_series(session_no_expire, tmdb_id="1002")
    await session_no_expire.commit()

    httpx_mock.add_response(
        url=f"{BRIDGE_BASE}/tmdb/movie/{movie.tmdb_id}",
        json=_movie_payload(tmdb_id="1001"),
        status_code=200,
    )
    httpx_mock.add_response(
        url=f"{BRIDGE_BASE}/tmdb/tv/{series.tmdb_id}",
        json=_series_payload(tmdb_id=1002, seasons=[]),
        status_code=200,
    )

    result = await update_tmdb_metadata(session_no_expire)

    # 1 movie + 1 series
    assert result.processed_count == 2
    assert result.skipped_count == 0
    assert result.failed_count == 0


async def test_orchestrator_skips_series_without_tmdb_id(
    session_no_expire: AsyncSession,
    httpx_mock,
) -> None:
    """Series without tmdb_id is not queried; only the movie is processed."""
    movie = await _create_movie(session_no_expire, tmdb_id="2001")

    # Series with no tmdb_id — should not be picked up
    media = MediaFactory.build(media_type=MediaType.SERIES, title="No TMDB Series")
    session_no_expire.add(media)
    await session_no_expire.flush()
    series_no_tmdb = SeriesFactory.build(
        id=media.id,
        tmdb_id=None,
        sonarr_id=None,
        tvdb_id=None,
        imdb_id=None,
        jellyfin_id=None,
        media=media,
    )
    session_no_expire.add(series_no_tmdb)
    await session_no_expire.flush()
    await session_no_expire.commit()

    httpx_mock.add_response(
        url=f"{BRIDGE_BASE}/tmdb/movie/{movie.tmdb_id}",
        json=_movie_payload(tmdb_id="2001"),
        status_code=200,
    )

    result = await update_tmdb_metadata(session_no_expire)

    # Only the movie was processed; series with no tmdb_id was skipped entirely
    assert result.processed_count == 1


# ===========================================================================
# Test 4: SyncSchedule with SyncJobType.TMDB_METADATA_UPDATE persists correctly
# ===========================================================================


async def test_sync_schedule_tmdb_metadata_update_persists(
    session_no_expire: AsyncSession,
) -> None:
    """SyncSchedule with TMDB_METADATA_UPDATE job_type round-trips through the DB."""
    schedule = SyncScheduleFactory.build(
        job_type=SyncJobType.TMDB_METADATA_UPDATE,
        preset=SchedulePreset.DAILY,
        cron_expression="0 1 * * *",
        is_running=False,
        last_run_at=None,
    )
    session_no_expire.add(schedule)
    await session_no_expire.commit()

    # Re-read from DB — verify enum value survived serialization
    result = await session_no_expire.execute(
        select(SyncSchedule).where(SyncSchedule.job_type == SyncJobType.TMDB_METADATA_UPDATE)
    )
    db_schedule = result.scalars().first()

    assert db_schedule is not None
    assert db_schedule.job_type == SyncJobType.TMDB_METADATA_UPDATE
    assert db_schedule.job_type.value == "tmdb_metadata_update"
    assert db_schedule.preset == SchedulePreset.DAILY
    assert db_schedule.cron_expression == "0 1 * * *"
    assert db_schedule.is_running is False


async def test_sync_schedule_tmdb_metadata_update_is_unique(
    session_no_expire: AsyncSession,
) -> None:
    """Only one SyncSchedule per job_type (unique constraint)."""
    import sqlalchemy.exc

    schedule1 = SyncScheduleFactory.build(
        job_type=SyncJobType.TMDB_METADATA_UPDATE,
        cron_expression="0 1 * * *",
    )
    schedule2 = SyncScheduleFactory.build(
        job_type=SyncJobType.TMDB_METADATA_UPDATE,
        cron_expression="0 2 * * *",
    )
    session_no_expire.add(schedule1)
    await session_no_expire.commit()

    session_no_expire.add(schedule2)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        await session_no_expire.flush()


# ===========================================================================
# Edge cases: bridge returns 404 or error
# ===========================================================================


async def test_series_skipped_when_bridge_returns_404(
    session_no_expire: AsyncSession,
    httpx_mock,
) -> None:
    """If bridge returns 404, the series is counted as skipped, not failed."""
    series = await _create_series(session_no_expire, tmdb_id="4040")
    await session_no_expire.commit()

    httpx_mock.add_response(
        url=f"{BRIDGE_BASE}/tmdb/tv/{series.tmdb_id}",
        status_code=404,
    )

    result = await update_series_tmdb_metadata(session_no_expire)

    assert result.skipped_count == 1
    assert result.failed_count == 0
    assert result.updated_count == 0

    # No seasons were created
    seasons = list(
        (await session_no_expire.execute(select(Season).where(Season.series_id == series.id)))
        .scalars()
        .all()
    )
    assert len(seasons) == 0


async def test_series_failed_when_bridge_returns_500(
    session_no_expire: AsyncSession,
    httpx_mock,
) -> None:
    """If bridge returns 5xx, the series is counted as failed."""
    series = await _create_series(session_no_expire, tmdb_id="5050")
    await session_no_expire.commit()

    httpx_mock.add_response(
        url=f"{BRIDGE_BASE}/tmdb/tv/{series.tmdb_id}",
        status_code=500,
    )

    result = await update_series_tmdb_metadata(session_no_expire)

    assert result.failed_count == 1
    assert result.skipped_count == 0
    assert result.updated_count == 0


async def test_series_without_tmdb_id_not_processed(
    session_no_expire: AsyncSession,
    httpx_mock,
) -> None:
    """Series with tmdb_id=None are not queried and not processed."""
    media = MediaFactory.build(media_type=MediaType.SERIES, title="No TMDB")
    session_no_expire.add(media)
    await session_no_expire.flush()
    series = SeriesFactory.build(
        id=media.id,
        tmdb_id=None,
        sonarr_id=None,
        tvdb_id=None,
        imdb_id=None,
        jellyfin_id=None,
        media=media,
    )
    session_no_expire.add(series)
    await session_no_expire.commit()

    result = await update_series_tmdb_metadata(session_no_expire)

    assert result.processed_count == 0
    # No HTTP request should have been made
    assert len(httpx_mock.get_requests()) == 0


async def test_existing_episodes_not_duplicated_on_rerun(
    session_no_expire: AsyncSession,
    httpx_mock,
) -> None:
    """Re-running job when season+episode already exist in DB does not duplicate them."""
    series = await _create_series(session_no_expire, tmdb_id="6060")

    # Pre-populate season and episode that bridge will also return
    season = Season(
        series_id=series.id,
        number=1,
        tmdb_id=401,
        jellyfin_id=None,
        overview=None,
        poster_url=None,
        vote_average=None,
        release_date=None,
    )
    session_no_expire.add(season)
    await session_no_expire.flush()

    episode = Episode(
        season_id=season.id,
        number=1,
        title="Pilot",
        tmdb_id=None,
        air_date=None,
        overview=None,
        episode_type=None,
        still_url=None,
        vote_average=None,
    )
    session_no_expire.add(episode)
    await session_no_expire.commit()

    payload = _series_payload(
        tmdb_id=6060,
        seasons=[
            _season_payload(
                1,
                401,
                [_episode_payload(1, 1, "Pilot")],
            )
        ],
    )
    httpx_mock.add_response(
        url=f"{BRIDGE_BASE}/tmdb/tv/{series.tmdb_id}",
        json=payload,
        status_code=200,
    )

    await update_series_tmdb_metadata(session_no_expire)

    # Still exactly 1 season and 1 episode
    seasons_count = (
        (await session_no_expire.execute(select(Season).where(Season.series_id == series.id)))
        .scalars()
        .all()
    )
    assert len(seasons_count) == 1

    episodes_count = (
        (await session_no_expire.execute(select(Episode).where(Episode.season_id == season.id)))
        .scalars()
        .all()
    )
    assert len(episodes_count) == 1


async def test_series_fields_updated_in_db(
    session_no_expire: AsyncSession,
    httpx_mock,
) -> None:
    """After job runs, series-level fields (title, rating, status) are persisted."""
    series = await _create_series(session_no_expire, tmdb_id="7070", title="Old Title")
    await session_no_expire.commit()

    payload = {
        "tmdb_id": 7070,
        "name": "New Title",
        "status": "Ended",
        "vote_average": 9.1,
        "genres": [{"id": 18, "name": "Drama"}],
        "seasons": [],
    }
    httpx_mock.add_response(
        url=f"{BRIDGE_BASE}/tmdb/tv/{series.tmdb_id}",
        json=payload,
        status_code=200,
    )

    await update_series_tmdb_metadata(session_no_expire)

    # Re-read from DB
    db_series = await session_no_expire.execute(
        select(Series).where(Series.id == series.id).options(selectinload(Series.media))
    )
    updated = db_series.scalars().first()
    assert updated is not None
    assert updated.media.title == "New Title"
    assert updated.rating_value == 9.1
    assert updated.tmdb_metadata_fetched_at is not None
    assert updated.status == SeriesStatus.ENDED


async def test_tmdb_metadata_fetched_at_is_set_after_run(
    session_no_expire: AsyncSession,
    httpx_mock,
) -> None:
    """tmdb_metadata_fetched_at is always set (even if no field data changed)."""
    series = await _create_series(session_no_expire, tmdb_id="3030")
    assert series.tmdb_metadata_fetched_at is None
    await session_no_expire.commit()

    # Payload with no new data (empty name, no fields that differ)
    payload: dict[str, object] = {
        "tmdb_id": 3030,
        "name": None,
        "status": None,
        "vote_average": None,
        "genres": [],
        "seasons": [],
    }
    httpx_mock.add_response(
        url=f"{BRIDGE_BASE}/tmdb/tv/{series.tmdb_id}",
        json=payload,
        status_code=200,
    )

    await update_series_tmdb_metadata(session_no_expire)

    db_series = (
        (await session_no_expire.execute(select(Series).where(Series.id == series.id)))
        .scalars()
        .first()
    )
    assert db_series is not None
    assert db_series.tmdb_metadata_fetched_at is not None
    assert db_series.tmdb_metadata_fetched_at.tzinfo is not None
