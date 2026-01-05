from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Episode, Media, MediaType, Season, Series


@pytest.mark.asyncio
async def test_import_sonarr_series_creates_new_series_with_episodes(
    client_with_db,
    session_for_test,
    monkeypatch,
):
    sonarr_series = [
        {
            "id": 1,
            "title": "Test Series",
            "tvdbId": 100,
            "imdbId": "tt0000100",
            "tmdbId": 200,
            "year": 2021,
            "status": "continuing",
            "genres": ["Drama"],
            "ratings": {"value": 8.5, "votes": 100},
            "images": [{"coverType": "poster", "remoteUrl": "http://poster.jpg"}],
            "seasons": [{"seasonNumber": 1}],
        }
    ]

    sonarr_episodes = [
        {
            "id": 10,
            "seasonNumber": 1,
            "episodeNumber": 1,
            "title": "Pilot",
            "airDateUtc": "2021-01-01T00:00:00Z",
            "overview": "Episode 1",
        },
        {
            "id": 11,
            "seasonNumber": 1,
            "episodeNumber": 2,
            "title": "Episode 2",
            "airDateUtc": "2021-01-08T00:00:00Z",
            "overview": "Episode 2",
        },
    ]

    monkeypatch.setattr(
        "app.services.sonarr_service.fetch_sonarr_series",
        AsyncMock(return_value=sonarr_series),
    )
    monkeypatch.setattr(
        "app.services.sonarr_service.fetch_sonarr_episodes",
        AsyncMock(return_value=sonarr_episodes),
    )

    resp = await client_with_db.post("/api/v1/sonarr/import")
    assert resp.status_code == 200
    assert resp.json() == {
        "new_series": 1,
        "updated_series": 0,
        "new_episodes": 2,
        "updated_episodes": 0,
    }

    series = (
        await session_for_test.execute(select(Series).options(selectinload(Series.media)))
    ).scalar_one()

    assert series.sonarr_id == 1
    assert series.tvdb_id == "100"
    assert series.imdb_id == "tt0000100"
    assert series.year == 2021
    assert series.genres == ["Drama"]
    assert series.rating_value == 8.5
    assert series.rating_votes == 100
    assert series.media.title == "Test Series"

    seasons = (await session_for_test.execute(select(Season))).scalars().all()
    assert len(seasons) == 1
    assert seasons[0].number == 1

    episodes = (await session_for_test.execute(select(Episode))).scalars().all()
    assert len(episodes) == 2


@pytest.mark.asyncio
async def test_import_sonarr_series_updates_existing_series_by_sonarr_id(
    client_with_db,
    session_for_test,
    monkeypatch,
):
    media = Media(media_type=MediaType.SERIES, title="Old Title")
    session_for_test.add(media)
    await session_for_test.flush()

    series = Series(id=media.id, sonarr_id=1, status="ended")
    session_for_test.add(series)
    await session_for_test.commit()

    sonarr_series = [
        {
            "id": 1,
            "title": "New Title",
            "status": "continuing",
            "seasons": [],
        }
    ]

    monkeypatch.setattr(
        "app.services.sonarr_service.fetch_sonarr_series",
        AsyncMock(return_value=sonarr_series),
    )
    monkeypatch.setattr(
        "app.services.sonarr_service.fetch_sonarr_episodes",
        AsyncMock(return_value=[]),
    )

    resp = await client_with_db.post("/api/v1/sonarr/import")
    assert resp.json()["updated_series"] == 1

    updated = (
        await session_for_test.execute(select(Series).options(selectinload(Series.media)))
    ).scalar_one()

    assert updated.media.title == "New Title"
    assert updated.status == "continuing"


@pytest.mark.asyncio
async def test_import_sonarr_series_updates_by_external_ids(
    client_with_db,
    session_for_test,
    monkeypatch,
):
    media = Media(media_type=MediaType.SERIES, title="Existing")
    session_for_test.add(media)
    await session_for_test.flush()

    series = Series(id=media.id, tvdb_id="100")
    session_for_test.add(series)
    await session_for_test.commit()

    sonarr_series = [
        {
            "id": 2,
            "title": "Existing Updated",
            "tvdbId": 100,
            "seasons": [],
        }
    ]

    monkeypatch.setattr(
        "app.services.sonarr_service.fetch_sonarr_series",
        AsyncMock(return_value=sonarr_series),
    )
    monkeypatch.setattr(
        "app.services.sonarr_service.fetch_sonarr_episodes",
        AsyncMock(return_value=[]),
    )

    resp = await client_with_db.post("/api/v1/sonarr/import")
    assert resp.json()["updated_series"] == 1

    updated = (
        await session_for_test.execute(select(Series).options(selectinload(Series.media)))
    ).scalar_one()

    assert updated.sonarr_id == 2
    assert updated.media.title == "Existing Updated"


@pytest.mark.asyncio
async def test_import_sonarr_series_updates_existing_episode(
    client_with_db,
    session_for_test,
    monkeypatch,
):
    media = Media(media_type=MediaType.SERIES, title="Series")
    session_for_test.add(media)
    await session_for_test.flush()

    series = Series(id=media.id, sonarr_id=1)
    session_for_test.add(series)
    await session_for_test.flush()

    season = Season(series_id=series.id, number=1)
    session_for_test.add(season)
    await session_for_test.flush()

    episode = Episode(
        season_id=season.id,
        sonarr_id=10,
        number=1,
        title="Old title",
    )
    session_for_test.add(episode)
    await session_for_test.commit()

    monkeypatch.setattr(
        "app.services.sonarr_service.fetch_sonarr_series",
        AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "title": "Series",
                    "seasons": [{"seasonNumber": 1}],
                }
            ]
        ),
    )
    monkeypatch.setattr(
        "app.services.sonarr_service.fetch_sonarr_episodes",
        AsyncMock(
            return_value=[
                {
                    "id": 10,
                    "seasonNumber": 1,
                    "episodeNumber": 1,
                    "title": "New title",
                }
            ]
        ),
    )

    resp = await client_with_db.post("/api/v1/sonarr/import")
    assert resp.json()["updated_episodes"] == 1

    ep = (await session_for_test.execute(select(Episode))).scalar_one()
    assert ep.title == "New title"
