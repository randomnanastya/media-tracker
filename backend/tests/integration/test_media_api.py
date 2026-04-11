from app.models import WatchStatus
from tests.factories import UserFactory, WatchHistoryFactory
from tests.integration.conftest import (
    create_episode,
    create_movie,
    create_season,
    create_series,
)


async def test_get_media_empty_db(client_with_db, session_for_test):
    resp = await client_with_db.get("/api/v1/media")
    assert resp.status_code == 200
    assert resp.json() == {"items": [], "total": 0}


async def test_get_media_returns_movie(client_with_db, session_for_test):
    await create_movie(session_for_test, title="Test Movie")

    resp = await client_with_db.get("/api/v1/media")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["title"] == "Test Movie"
    assert item["media_type"] == "movie"
    assert item["watch_status"] is None


async def test_get_media_returns_series(client_with_db, session_for_test):
    series = await create_series(session_for_test, title="Test Series")
    season = await create_season(session_for_test, series_id=series.id)
    await create_episode(session_for_test, season_id=season.id)

    resp = await client_with_db.get("/api/v1/media")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["title"] == "Test Series"
    assert item["media_type"] == "series"


async def test_get_media_filter_by_type_movie(client_with_db, session_for_test):
    await create_movie(session_for_test, title="Only Movie")
    await create_series(session_for_test, title="Some Series")

    resp = await client_with_db.get("/api/v1/media", params={"type": "movie"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["media_type"] == "movie"
    assert data["items"][0]["title"] == "Only Movie"


async def test_get_media_filter_by_type_series(client_with_db, session_for_test):
    await create_movie(session_for_test, title="Some Movie")
    await create_series(session_for_test, title="Only Series")

    resp = await client_with_db.get("/api/v1/media", params={"type": "series"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["media_type"] == "series"
    assert data["items"][0]["title"] == "Only Series"


async def test_get_media_movie_with_watched_status(client_with_db, session_for_test):
    user = UserFactory.build()
    session_for_test.add(user)
    await session_for_test.flush()

    movie = await create_movie(session_for_test, title="Watched Movie")

    wh = WatchHistoryFactory.build(
        user_id=user.id, media_id=movie.id, episode_id=None, status=WatchStatus.WATCHED
    )
    session_for_test.add(wh)
    await session_for_test.flush()

    resp = await client_with_db.get("/api/v1/media")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["watch_status"] == "watched"


async def test_get_media_filter_by_status_watched(client_with_db, session_for_test):
    user = UserFactory.build()
    session_for_test.add(user)
    await session_for_test.flush()

    watched_movie = await create_movie(session_for_test, title="Watched Movie")
    planned_movie = await create_movie(session_for_test, title="Planned Movie")

    wh_watched = WatchHistoryFactory.build(
        user_id=user.id, media_id=watched_movie.id, episode_id=None, status=WatchStatus.WATCHED
    )
    session_for_test.add(wh_watched)

    wh_planned = WatchHistoryFactory.build(
        user_id=user.id, media_id=planned_movie.id, episode_id=None, status=WatchStatus.PLANNED
    )
    session_for_test.add(wh_planned)
    await session_for_test.flush()

    resp = await client_with_db.get("/api/v1/media", params={"status": "watched"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Watched Movie"
    assert data["items"][0]["watch_status"] == "watched"


async def test_get_media_series_all_episodes_watched(client_with_db, session_for_test):
    user = UserFactory.build()
    session_for_test.add(user)
    await session_for_test.flush()

    series = await create_series(session_for_test, title="Fully Watched Series")
    season = await create_season(session_for_test, series_id=series.id)
    episode1 = await create_episode(session_for_test, season_id=season.id, number=1, title="Ep 1")
    episode2 = await create_episode(session_for_test, season_id=season.id, number=2, title="Ep 2")

    wh1 = WatchHistoryFactory.build(
        user_id=user.id, media_id=series.id, episode_id=episode1.id, status=WatchStatus.WATCHED
    )
    session_for_test.add(wh1)

    wh2 = WatchHistoryFactory.build(
        user_id=user.id, media_id=series.id, episode_id=episode2.id, status=WatchStatus.WATCHED
    )
    session_for_test.add(wh2)
    await session_for_test.flush()

    resp = await client_with_db.get("/api/v1/media")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["title"] == "Fully Watched Series"
    assert item["watch_status"] == "watched"
