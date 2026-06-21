"""Unit tests for watch_history API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.models.user import WatchHistory, WatchStatus
from app.schemas.watch_history import BulkWatchStatusResponse
from tests.factories import WatchHistoryFactory


def _make_watch_history(
    media_id: int = 1,
    episode_id: int | None = None,
    status: WatchStatus = WatchStatus.WATCHED,
    is_manual: bool = True,
    watched_at: object = None,
) -> WatchHistory:
    return WatchHistoryFactory.build(
        media_id=media_id,
        episode_id=episode_id,
        status=status,
        is_manual=is_manual,
        watched_at=watched_at,
    )


# ─── PUT /movies/{media_id} ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_set_movie_watched_success(async_client: AsyncClient) -> None:
    """PUT movies/1 status=watched → 200 WatchStatusUpdateResponse."""
    wh = _make_watch_history(media_id=1, status=WatchStatus.WATCHED, is_manual=True)

    with patch(
        "app.api.watch_history.watch_history_service.set_movie_watch_status",
        new_callable=AsyncMock,
        return_value=wh,
    ):
        response = await async_client.put(
            "/api/v1/watch/movies/1",
            json={"jellyfin_user_id": "some-uuid", "status": "watched"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "item" in data
    assert data["item"]["media_id"] == 1
    assert data["item"]["status"] == "watched"
    assert data["item"]["is_manual"] is True


@pytest.mark.asyncio
async def test_set_movie_planned_success(async_client: AsyncClient) -> None:
    """PUT movies/1 status=planned → 200 с статусом planned."""
    wh = _make_watch_history(
        media_id=1, status=WatchStatus.PLANNED, is_manual=True, watched_at=None
    )

    with patch(
        "app.api.watch_history.watch_history_service.set_movie_watch_status",
        new_callable=AsyncMock,
        return_value=wh,
    ):
        response = await async_client.put(
            "/api/v1/watch/movies/1",
            json={"jellyfin_user_id": "some-uuid", "status": "planned"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["item"]["status"] == "planned"
    assert data["item"]["watched_at"] is None


@pytest.mark.asyncio
async def test_set_movie_watching_success(async_client: AsyncClient) -> None:
    """PUT movies/1 status=watching → 200 с статусом watching."""
    wh = _make_watch_history(
        media_id=1, status=WatchStatus.WATCHING, is_manual=True, watched_at=None
    )

    with patch(
        "app.api.watch_history.watch_history_service.set_movie_watch_status",
        new_callable=AsyncMock,
        return_value=wh,
    ):
        response = await async_client.put(
            "/api/v1/watch/movies/1",
            json={"jellyfin_user_id": "some-uuid", "status": "watching"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["item"]["status"] == "watching"
    assert data["item"]["watched_at"] is None


@pytest.mark.asyncio
async def test_set_movie_dropped_success(async_client: AsyncClient) -> None:
    """PUT movies/1 status=dropped → 200 с статусом dropped."""
    wh = _make_watch_history(
        media_id=1, status=WatchStatus.DROPPED, is_manual=True, watched_at=None
    )

    with patch(
        "app.api.watch_history.watch_history_service.set_movie_watch_status",
        new_callable=AsyncMock,
        return_value=wh,
    ):
        response = await async_client.put(
            "/api/v1/watch/movies/1",
            json={"jellyfin_user_id": "some-uuid", "status": "dropped"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["item"]["status"] == "dropped"
    assert data["item"]["watched_at"] is None


@pytest.mark.asyncio
async def test_set_movie_user_not_found(async_client: AsyncClient) -> None:
    """Если сервис поднимает HTTPException(404) → ответ 404."""
    with patch(
        "app.api.watch_history.watch_history_service.set_movie_watch_status",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=404, detail={"code": "WATCH_USER_NOT_FOUND"}),
    ):
        response = await async_client.put(
            "/api/v1/watch/movies/1",
            json={"jellyfin_user_id": "nonexistent-uuid", "status": "watched"},
        )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "WATCH_USER_NOT_FOUND"


# ─── DELETE /movies/{media_id}/manual ──────────────────────────────────────


@pytest.mark.asyncio
async def test_clear_movie_manual_success(async_client: AsyncClient) -> None:
    """DELETE movies/1/manual → 204 No Content."""
    with patch(
        "app.api.watch_history.watch_history_service.clear_movie_manual_flag",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = await async_client.delete(
            "/api/v1/watch/movies/1/manual",
            params={"jellyfin_user_id": "some-uuid"},
        )

    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.asyncio
async def test_clear_movie_manual_not_found(async_client: AsyncClient) -> None:
    """Сервис поднимает HTTPException(404) → ответ 404."""
    with patch(
        "app.api.watch_history.watch_history_service.clear_movie_manual_flag",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=404, detail={"code": "WATCH_USER_NOT_FOUND"}),
    ):
        response = await async_client.delete(
            "/api/v1/watch/movies/1/manual",
            params={"jellyfin_user_id": "nonexistent-uuid"},
        )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "WATCH_USER_NOT_FOUND"


# ─── PUT /episodes/{episode_id} ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_set_episode_watched_success(async_client: AsyncClient) -> None:
    """PUT episodes/1 status=watched → 200 WatchStatusUpdateResponse."""
    wh = _make_watch_history(media_id=10, episode_id=1, status=WatchStatus.WATCHED, is_manual=True)

    with patch(
        "app.api.watch_history.watch_history_service.set_episode_watch_status",
        new_callable=AsyncMock,
        return_value=wh,
    ):
        response = await async_client.put(
            "/api/v1/watch/episodes/1",
            json={"jellyfin_user_id": "some-uuid", "status": "watched"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["item"]["episode_id"] == 1
    assert data["item"]["status"] == "watched"
    assert data["item"]["is_manual"] is True


# ─── DELETE /episodes/{episode_id}/manual ──────────────────────────────────


@pytest.mark.asyncio
async def test_clear_episode_manual_success(async_client: AsyncClient) -> None:
    """DELETE episodes/1/manual → 204."""
    with patch(
        "app.api.watch_history.watch_history_service.clear_episode_manual_flag",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = await async_client.delete(
            "/api/v1/watch/episodes/1/manual",
            params={"jellyfin_user_id": "some-uuid"},
        )

    assert response.status_code == 204
    assert response.content == b""


# ─── PUT /seasons/{season_id} ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_set_season_watch_status(async_client: AsyncClient) -> None:
    """PUT seasons/1 → 200 BulkWatchStatusResponse."""
    bulk_result = BulkWatchStatusResponse(affected=5, inserted=3, updated=2)

    with patch(
        "app.api.watch_history.watch_history_service.set_season_watch_status",
        new_callable=AsyncMock,
        return_value=bulk_result,
    ):
        response = await async_client.put(
            "/api/v1/watch/seasons/1",
            json={"jellyfin_user_id": "some-uuid", "status": "watched"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["affected"] == 5
    assert data["inserted"] == 3
    assert data["updated"] == 2


# ─── DELETE /seasons/{season_id}/manual ────────────────────────────────────


@pytest.mark.asyncio
async def test_clear_season_manual_flag(async_client: AsyncClient) -> None:
    """DELETE seasons/1/manual → 200 BulkWatchStatusResponse."""
    bulk_result = BulkWatchStatusResponse(affected=4, inserted=0, updated=4)

    with patch(
        "app.api.watch_history.watch_history_service.clear_season_manual_flag",
        new_callable=AsyncMock,
        return_value=bulk_result,
    ):
        response = await async_client.delete(
            "/api/v1/watch/seasons/1/manual",
            params={"jellyfin_user_id": "some-uuid"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["affected"] == 4
    assert data["inserted"] == 0
    assert data["updated"] == 4


# ─── PUT /series/{media_id} ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_set_series_watch_status(async_client: AsyncClient) -> None:
    """PUT series/1 → 200 BulkWatchStatusResponse."""
    bulk_result = BulkWatchStatusResponse(affected=10, inserted=10, updated=0)

    with patch(
        "app.api.watch_history.watch_history_service.set_series_watch_status",
        new_callable=AsyncMock,
        return_value=bulk_result,
    ):
        response = await async_client.put(
            "/api/v1/watch/series/1",
            json={"jellyfin_user_id": "some-uuid", "status": "watched"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["affected"] == 10
    assert data["inserted"] == 10
    assert data["updated"] == 0


# ─── DELETE /series/{media_id}/manual ──────────────────────────────────────


@pytest.mark.asyncio
async def test_clear_series_manual_flag(async_client: AsyncClient) -> None:
    """DELETE series/1/manual → 200 BulkWatchStatusResponse."""
    bulk_result = BulkWatchStatusResponse(affected=7, inserted=0, updated=7)

    with patch(
        "app.api.watch_history.watch_history_service.clear_series_manual_flag",
        new_callable=AsyncMock,
        return_value=bulk_result,
    ):
        response = await async_client.delete(
            "/api/v1/watch/series/1/manual",
            params={"jellyfin_user_id": "some-uuid"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["affected"] == 7
    assert data["inserted"] == 0
    assert data["updated"] == 7
