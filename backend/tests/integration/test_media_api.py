from app.models import MediaType, MovieStatus, SeriesStatus, WatchStatus
from tests.factories import (
    MediaFactory,
    MovieFactory,
    SeriesFactory,
    UserFactory,
    WatchHistoryFactory,
)
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


async def test_get_media_detail_movie_basic(client_with_db, session_for_test):
    movie = await create_movie(session_for_test, title="Basic Movie")

    resp = await client_with_db.get(f"/api/v1/media/{movie.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == movie.id
    assert data["title"] == "Basic Movie"
    assert data["media_type"] == "movie"
    assert data["tvdb_id"] is None


async def test_get_media_detail_series_basic(client_with_db, session_for_test):
    series = await create_series(session_for_test, title="Basic Series")

    resp = await client_with_db.get(f"/api/v1/media/{series.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["media_type"] == "series"
    assert data["tvdb_id"] == series.tvdb_id


async def test_get_media_detail_404(client_with_db, session_for_test):
    resp = await client_with_db.get("/api/v1/media/999999")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Media not found"}


async def test_get_media_detail_movie_watch_status(client_with_db, session_for_test):
    user = UserFactory.build()
    session_for_test.add(user)
    await session_for_test.flush()

    movie = await create_movie(session_for_test, title="Planned Movie")

    wh = WatchHistoryFactory.build(
        user_id=user.id, media_id=movie.id, episode_id=None, status=WatchStatus.PLANNED
    )
    session_for_test.add(wh)
    await session_for_test.flush()

    resp = await client_with_db.get(f"/api/v1/media/{movie.id}")
    assert resp.status_code == 200
    assert resp.json()["watch_status"] == "planned"


async def test_get_media_detail_series_watch_status(client_with_db, session_for_test):
    user = UserFactory.build()
    session_for_test.add(user)
    await session_for_test.flush()

    series = await create_series(session_for_test, title="Watched Series")
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

    resp = await client_with_db.get(f"/api/v1/media/{series.id}")
    assert resp.status_code == 200
    assert resp.json()["watch_status"] == "watched"


async def test_get_media_detail_rating_percent_null(client_with_db, session_for_test):
    media = MediaFactory(media_type=MediaType.MOVIE, title="No Rating Movie")
    session_for_test.add(media)
    await session_for_test.flush()
    movie = MovieFactory.build(id=media.id, rating_value=None, media=media)
    session_for_test.add(movie)
    await session_for_test.flush()

    resp = await client_with_db.get(f"/api/v1/media/{media.id}")
    assert resp.status_code == 200
    assert resp.json()["tmdb_rating_percent"] is None


async def test_get_media_detail_rating_percent_computed(client_with_db, session_for_test):
    media = MediaFactory(media_type=MediaType.MOVIE, title="Rated Movie")
    session_for_test.add(media)
    await session_for_test.flush()
    movie = MovieFactory.build(id=media.id, rating_value=7.5, media=media)
    session_for_test.add(movie)
    await session_for_test.flush()

    resp = await client_with_db.get(f"/api/v1/media/{media.id}")
    assert resp.status_code == 200
    assert resp.json()["tmdb_rating_percent"] == 75


async def test_get_media_detail_status_lowercase(client_with_db, session_for_test):
    media = MediaFactory(media_type=MediaType.MOVIE, title="Released Movie")
    session_for_test.add(media)
    await session_for_test.flush()
    movie = MovieFactory.build(id=media.id, status=MovieStatus.RELEASED, media=media)
    session_for_test.add(movie)
    await session_for_test.flush()

    resp = await client_with_db.get(f"/api/v1/media/{media.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "released"


async def test_get_media_detail_invalid_id(client_with_db, session_for_test):
    resp = await client_with_db.get("/api/v1/media/abc")
    assert resp.status_code == 422


async def test_get_media_detail_series_status_lowercase(client_with_db, session_for_test):
    media = MediaFactory(media_type=MediaType.SERIES, title="Ended Series")
    session_for_test.add(media)
    await session_for_test.flush()
    series = SeriesFactory.build(id=media.id, status=SeriesStatus.ENDED, media=media)
    session_for_test.add(series)
    await session_for_test.flush()

    resp = await client_with_db.get(f"/api/v1/media/{media.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ended"


async def test_get_media_detail_genres_returned_as_list(client_with_db, session_for_test):
    media = MediaFactory(media_type=MediaType.SERIES, title="Genre Series")
    session_for_test.add(media)
    await session_for_test.flush()
    series = SeriesFactory.build(id=media.id, genres=["Drama", "Thriller"], media=media)
    session_for_test.add(series)
    await session_for_test.flush()

    resp = await client_with_db.get(f"/api/v1/media/{media.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["genres"], list)
    assert set(data["genres"]) == {"Drama", "Thriller"}


async def test_get_media_detail_no_watch_history_watch_status_is_none(
    client_with_db, session_for_test
):
    movie = await create_movie(session_for_test, title="Unwatched Movie")

    resp = await client_with_db.get(f"/api/v1/media/{movie.id}")
    assert resp.status_code == 200
    assert resp.json()["watch_status"] is None


async def test_get_media_detail_series_tvdb_id_null(client_with_db, session_for_test):
    media = MediaFactory(media_type=MediaType.SERIES, title="No TVDB Series")
    session_for_test.add(media)
    await session_for_test.flush()
    series = SeriesFactory.build(id=media.id, tvdb_id=None, media=media)
    session_for_test.add(series)
    await session_for_test.flush()

    resp = await client_with_db.get(f"/api/v1/media/{media.id}")
    assert resp.status_code == 200
    assert resp.json()["tvdb_id"] is None


async def test_get_media_detail_movie_tvdb_id_always_null(client_with_db, session_for_test):
    movie = await create_movie(session_for_test, title="Movie No TVDB")

    resp = await client_with_db.get(f"/api/v1/media/{movie.id}")
    assert resp.status_code == 200
    assert resp.json()["tvdb_id"] is None


async def test_get_media_detail_movie_two_users_returns_highest_priority_status(
    client_with_db, session_for_test
):
    user1 = UserFactory.build()
    user2 = UserFactory.build()
    session_for_test.add(user1)
    session_for_test.add(user2)
    await session_for_test.flush()

    movie = await create_movie(session_for_test, title="Shared Movie")

    wh1 = WatchHistoryFactory.build(
        user_id=user1.id, media_id=movie.id, episode_id=None, status=WatchStatus.WATCHED
    )
    wh2 = WatchHistoryFactory.build(
        user_id=user2.id, media_id=movie.id, episode_id=None, status=WatchStatus.PLANNED
    )
    session_for_test.add(wh1)
    session_for_test.add(wh2)
    await session_for_test.flush()

    resp = await client_with_db.get(f"/api/v1/media/{movie.id}")
    assert resp.status_code == 200
    assert resp.json()["watch_status"] == "watched"
