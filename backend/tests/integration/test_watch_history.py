"""Integration tests for watch history manual override endpoints and sync protection."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.models.user import WatchHistory, WatchStatus
from app.services.sync_jellyfin_watched_movies_service import sync_jellyfin_watched_movies
from tests.factories import JellyfinMovieDictFactory, WatchHistoryFactory
from tests.integration.conftest import (
    create_episode,
    create_movie,
    create_season,
    create_series,
    create_user,
)


@pytest.fixture(autouse=True)
def mock_jellyfin_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock config for sync service used in several tests."""
    monkeypatch.setattr(
        "app.services.sync_jellyfin_watched_movies_service.get_decrypted_config",
        AsyncMock(return_value=("http://jellyfin:8096", "test-api-key")),
    )


# --- Test 1: PUT /movies creates record with is_manual=True ------------------


async def test_set_movie_watched_creates_record(client_with_db, session_for_test) -> None:
    """PUT /api/v1/watch/movies/{id} creates WatchHistory: is_manual=True, status=WATCHED."""
    user = await create_user(session_for_test, username="alice", jellyfin_user_id=str(uuid.uuid4()))
    movie = await create_movie(session_for_test, title="Inception")
    jf_user_id = user.jellyfin_user_id
    movie_id = movie.id
    user_id = user.id
    await session_for_test.commit()

    response = await client_with_db.put(
        f"/api/v1/watch/movies/{movie_id}",
        json={"jellyfin_user_id": jf_user_id, "status": "watched"},
    )

    assert response.status_code == 200

    rows = (await session_for_test.execute(select(WatchHistory))).scalars().all()
    assert len(rows) == 1
    wh = rows[0]
    assert wh.is_manual is True
    assert wh.status == WatchStatus.WATCHED
    assert wh.watched_at is not None
    assert wh.media_id == movie_id
    assert wh.user_id == user_id


# --- Test 2: PUT is idempotent — no duplicate rows created -------------------


async def test_set_movie_watched_is_idempotent(client_with_db, session_for_test) -> None:
    """Two PUT requests → single row in DB (upsert), fields correctly set."""
    user = await create_user(session_for_test, username="bob", jellyfin_user_id=str(uuid.uuid4()))
    movie = await create_movie(session_for_test, title="Matrix")
    jf_user_id = user.jellyfin_user_id
    movie_id = movie.id
    await session_for_test.commit()

    payload = {"jellyfin_user_id": jf_user_id, "status": "watched"}

    r1 = await client_with_db.put(f"/api/v1/watch/movies/{movie_id}", json=payload)
    assert r1.status_code == 200

    r2 = await client_with_db.put(f"/api/v1/watch/movies/{movie_id}", json=payload)
    assert r2.status_code == 200

    rows = (await session_for_test.execute(select(WatchHistory))).scalars().all()
    assert len(rows) == 1
    wh = rows[0]
    assert wh.status == WatchStatus.WATCHED
    assert wh.is_manual is True
    assert wh.media_id == movie_id


# --- Test 3: DELETE /manual resets is_manual flag, status unchanged ----------


async def test_clear_movie_manual_flag(client_with_db, session_for_test) -> None:
    """SET watched -> DELETE manual -> is_manual=False, status stays WATCHED."""
    user = await create_user(
        session_for_test, username="charlie", jellyfin_user_id=str(uuid.uuid4())
    )
    movie = await create_movie(session_for_test, title="Interstellar")
    jf_uid = user.jellyfin_user_id
    movie_id = movie.id
    await session_for_test.commit()

    set_resp = await client_with_db.put(
        f"/api/v1/watch/movies/{movie_id}",
        json={"jellyfin_user_id": jf_uid, "status": "watched"},
    )
    assert set_resp.status_code == 200

    del_resp = await client_with_db.delete(
        f"/api/v1/watch/movies/{movie_id}/manual",
        params={"jellyfin_user_id": jf_uid},
    )
    assert del_resp.status_code == 204

    rows = (await session_for_test.execute(select(WatchHistory))).scalars().all()
    assert len(rows) == 1
    wh = rows[0]
    assert wh.is_manual is False
    assert wh.status == WatchStatus.WATCHED


# --- Test 4: is_manual protects record from sync -----------------------------


async def test_is_manual_protects_from_sync(session_for_test, monkeypatch) -> None:
    """is_manual=True record stays WATCHED; non-manual WATCHED → PLANNED after sync (Played=False)."""
    user = await create_user(session_for_test, username="dave", jellyfin_user_id="jf-dave")
    # Movie A — manual, should be protected
    movie_a = await create_movie(session_for_test, jellyfin_id="jf-movie-A", tmdb_id="tmdb-A")
    # Movie B — non-manual, sync should update status to PLANNED
    movie_b = await create_movie(session_for_test, jellyfin_id="jf-movie-B", tmdb_id="tmdb-B")

    wh_manual = WatchHistoryFactory.build(
        user_id=user.id,
        media_id=movie_a.id,
        episode_id=None,
        status=WatchStatus.WATCHED,
        is_manual=True,
        watched_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
    )
    wh_sync = WatchHistoryFactory.build(
        user_id=user.id,
        media_id=movie_b.id,
        episode_id=None,
        status=WatchStatus.WATCHED,
        is_manual=False,
        watched_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
    )
    session_for_test.add(wh_manual)
    session_for_test.add(wh_sync)
    await session_for_test.commit()

    # Sync reports both movies as UNWATCHED (Played=False) → jellyfin_status=PLANNED
    async def mock_fetch(url, api_key, jellyfin_user_id):
        return [
            JellyfinMovieDictFactory(
                Id="jf-movie-A",
                Name="Movie A",
                ProviderIds={"Tmdb": "tmdb-A"},
                UserData={"Played": False},
            ),
            JellyfinMovieDictFactory(
                Id="jf-movie-B",
                Name="Movie B",
                ProviderIds={"Tmdb": "tmdb-B"},
                UserData={"Played": False},
            ),
        ]

    monkeypatch.setattr(
        "app.services.sync_jellyfin_watched_movies_service.fetch_jellyfin_movies_for_user_all",
        mock_fetch,
    )

    await sync_jellyfin_watched_movies(session_for_test)
    await session_for_test.commit()

    await session_for_test.refresh(wh_manual)
    await session_for_test.refresh(wh_sync)

    # Manual record must not be touched
    assert wh_manual.status == WatchStatus.WATCHED
    assert wh_manual.is_manual is True

    # Non-manual record must be updated to PLANNED by sync
    assert wh_sync.status == WatchStatus.PLANNED


# --- Test 5: PUT season — bulk update all episodes ---------------------------


async def test_set_season_watch_status_bulk(client_with_db, session_for_test) -> None:
    """PUT /seasons/{id} updates all 3 episodes: affected=3, 3 rows in DB."""
    user = await create_user(session_for_test, username="eve", jellyfin_user_id=str(uuid.uuid4()))
    series = await create_series(session_for_test, title="Breaking Bad")
    season = await create_season(session_for_test, series_id=series.id, number=1)

    ep1 = await create_episode(session_for_test, season_id=season.id, number=1, title="Pilot")
    ep2 = await create_episode(session_for_test, season_id=season.id, number=2, title="S01E02")
    ep3 = await create_episode(session_for_test, season_id=season.id, number=3, title="S01E03")
    jf_user_id = user.jellyfin_user_id
    season_id = season.id
    ep1_id, ep2_id, ep3_id = ep1.id, ep2.id, ep3.id
    await session_for_test.commit()

    response = await client_with_db.put(
        f"/api/v1/watch/seasons/{season_id}",
        json={"jellyfin_user_id": jf_user_id, "status": "watched"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["affected"] == 3

    rows = (await session_for_test.execute(select(WatchHistory))).scalars().all()
    assert len(rows) == 3

    episode_ids_in_db = {row.episode_id for row in rows}
    assert episode_ids_in_db == {ep1_id, ep2_id, ep3_id}

    for row in rows:
        assert row.status == WatchStatus.WATCHED
        assert row.is_manual is True


# --- Test 6: Unknown jellyfin_user_id → 404 WATCH_USER_NOT_FOUND ------------


async def test_unknown_user_returns_404(client_with_db, session_for_test) -> None:
    """PUT with nonexistent jellyfin_user_id → 404, code=WATCH_USER_NOT_FOUND."""
    movie = await create_movie(session_for_test, title="Phantom Movie")
    movie_id = movie.id
    await session_for_test.commit()

    response = await client_with_db.put(
        f"/api/v1/watch/movies/{movie_id}",
        json={"jellyfin_user_id": str(uuid.uuid4()), "status": "watched"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "WATCH_USER_NOT_FOUND"


# --- Test 7: Nonexistent media_id → 404 WATCH_MEDIA_NOT_FOUND ---------------


async def test_nonexistent_movie_returns_404(client_with_db, session_for_test) -> None:
    """PUT with valid user but nonexistent movie_id → 404, code=WATCH_MEDIA_NOT_FOUND."""
    user = await create_user(session_for_test, username="frank", jellyfin_user_id=str(uuid.uuid4()))
    jf_user_id = user.jellyfin_user_id
    await session_for_test.commit()

    response = await client_with_db.put(
        "/api/v1/watch/movies/999999",
        json={"jellyfin_user_id": jf_user_id, "status": "watched"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "WATCH_MEDIA_NOT_FOUND"
