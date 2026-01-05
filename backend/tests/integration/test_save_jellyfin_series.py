from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Episode, Media, MediaType, Season, Series


@pytest.mark.asyncio
async def test_import_jellyfin_series_creates_new_series_with_episodes(
    client_with_db,
    session_for_test,
    monkeypatch,
):
    jellyfin_series = [
        {
            "Id": "jf-series-1",
            "Name": "Test Series",
            "PremiereDate": "2020-01-01T00:00:00Z",
            "ProductionYear": 2020,
            "Status": "Continuing",
            "ProviderIds": {
                "Tmdb": "100",
                "Tvdb": "200",
                "Imdb": "tt0000100",
            },
        }
    ]

    jellyfin_episodes = [
        {
            "Id": "ep-1",
            "SeasonId": "season-1",
            "ParentIndexNumber": 1,
            "IndexNumber": 1,
            "Name": "Pilot",
            "PremiereDate": "2020-01-01T00:00:00Z",
        },
        {
            "Id": "ep-2",
            "SeasonId": "season-1",
            "ParentIndexNumber": 1,
            "IndexNumber": 2,
            "Name": "Episode 2",
            "PremiereDate": "2020-01-08T00:00:00Z",
        },
    ]

    monkeypatch.setattr(
        "app.services.import_jellyfin_series_service.fetch_jellyfin_series",
        AsyncMock(return_value=jellyfin_series),
    )
    monkeypatch.setattr(
        "app.services.import_jellyfin_series_service.fetch_jellyfin_episodes",
        AsyncMock(return_value=jellyfin_episodes),
    )

    resp = await client_with_db.post("/api/v1/jellyfin/import/series")
    assert resp.status_code == 200
    assert resp.json() == {
        "new_series": 1,
        "updated_series": 0,
        "new_episodes": 2,
        "updated_episodes": 0,
    }

    # ----- DB assertions -----
    series = (
        await session_for_test.execute(select(Series).options(selectinload(Series.media)))
    ).scalar_one()

    assert series.jellyfin_id == "jf-series-1"
    assert series.tmdb_id == "100"
    assert series.tvdb_id == "200"
    assert series.imdb_id == "tt0000100"
    assert series.status == "Continuing"
    assert series.year == 2020
    assert series.media.title == "Test Series"

    seasons = (await session_for_test.execute(select(Season))).scalars().all()
    assert len(seasons) == 1
    assert seasons[0].number == 1

    episodes = (await session_for_test.execute(select(Episode))).scalars().all()
    assert len(episodes) == 2


@pytest.mark.asyncio
async def test_import_jellyfin_series_updates_existing_by_tmdb(
    client_with_db,
    session_for_test,
    monkeypatch,
):
    media = Media(media_type=MediaType.SERIES, title="Old Title")
    session_for_test.add(media)
    await session_for_test.flush()

    series = Series(
        id=media.id,
        tmdb_id="100",
        jellyfin_id=None,
        status=None,
        year=None,
    )
    session_for_test.add(series)
    await session_for_test.commit()

    jellyfin_series = [
        {
            "Id": "jf-series-1",
            "Name": "New Title",
            "ProductionYear": 2021,
            "Status": "Ended",
            "ProviderIds": {"Tmdb": "100"},
        }
    ]

    monkeypatch.setattr(
        "app.services.import_jellyfin_series_service.fetch_jellyfin_series",
        AsyncMock(return_value=jellyfin_series),
    )
    monkeypatch.setattr(
        "app.services.import_jellyfin_series_service.fetch_jellyfin_episodes",
        AsyncMock(return_value=[]),
    )

    resp = await client_with_db.post("/api/v1/jellyfin/import/series")
    assert resp.status_code == 200
    assert resp.json()["updated_series"] == 1

    updated = (
        await session_for_test.execute(select(Series).options(selectinload(Series.media)))
    ).scalar_one()

    assert updated.jellyfin_id == "jf-series-1"
    assert updated.media.title == "New Title"
    assert updated.status == "Ended"
    assert updated.year == 2021


@pytest.mark.asyncio
async def test_import_jellyfin_series_updates_existing_episode(
    client_with_db,
    session_for_test,
    monkeypatch,
):
    media = Media(media_type=MediaType.SERIES, title="Series")
    session_for_test.add(media)
    await session_for_test.flush()

    series = Series(id=media.id, jellyfin_id="jf-series-1")
    session_for_test.add(series)
    await session_for_test.flush()

    season = Season(series_id=series.id, number=1, jellyfin_id="season-1")
    session_for_test.add(season)
    await session_for_test.flush()

    episode = Episode(
        season_id=season.id,
        jellyfin_id="ep-1",
        number=1,
        title="Old title",
    )
    session_for_test.add(episode)
    await session_for_test.commit()

    monkeypatch.setattr(
        "app.services.import_jellyfin_series_service.fetch_jellyfin_series",
        AsyncMock(return_value=[{"Id": "jf-series-1", "Name": "Series"}]),
    )
    monkeypatch.setattr(
        "app.services.import_jellyfin_series_service.fetch_jellyfin_episodes",
        AsyncMock(
            return_value=[
                {
                    "Id": "ep-1",
                    "SeasonId": "season-1",
                    "ParentIndexNumber": 1,
                    "IndexNumber": 1,
                    "Name": "New title",
                }
            ]
        ),
    )

    resp = await client_with_db.post("/api/v1/jellyfin/import/series")
    assert resp.json()["updated_episodes"] == 1

    ep = (await session_for_test.execute(select(Episode))).scalar_one()
    assert ep.title == "New title"
