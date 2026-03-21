from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.error_codes import JellyfinErrorCode
from app.schemas.jellyfin import JellyfinWatchedMoviesResponse
from app.schemas.responses import ErrorDetail


@pytest.mark.asyncio
async def test_sync_jellyfin_watch_movies_success(
    async_client, override_session_dependency, mock_session
):
    """Успешная синхронизация просмотра фильмов."""
    mock_response = JellyfinWatchedMoviesResponse(
        total_users=2,
        total_movies_processed=50,
        watched_added=10,
        watched_updated=5,
        unwatched_marked=3,
    )

    with patch(
        "app.api.jellyfin.sync_jellyfin_watched_movies", new_callable=AsyncMock
    ) as mock_sync:
        mock_sync.return_value = mock_response

        response = await async_client.post("/api/v1/jellyfin/movies/watched")

        assert response.status_code == 200
        assert response.json() == mock_response.model_dump(mode="json", exclude_none=True)
        mock_sync.assert_awaited_once_with(mock_session)


@pytest.mark.asyncio
async def test_watched_movies_empty_result(async_client, override_session_dependency, mock_session):
    """Тест синхронизации, когда нет пользователей или фильмов."""
    # Arrange
    mock_response = JellyfinWatchedMoviesResponse(
        total_users=0,
        total_movies_processed=0,
        watched_added=0,
        watched_updated=0,
        unwatched_marked=0,
    )

    with patch(
        "app.api.jellyfin.sync_jellyfin_watched_movies", new_callable=AsyncMock
    ) as mock_sync:
        mock_sync.return_value = mock_response

        # Act
        response = await async_client.post("/api/v1/jellyfin/movies/watched")

        # Assert
        assert response.status_code == 200
        act_resp_body = response.json()

        assert act_resp_body == mock_response.model_dump(mode="json", exclude_none=True)
        mock_sync.assert_awaited_once_with(mock_session)


@pytest.mark.asyncio
async def test_watched_movies_service_error_sync(
    async_client, override_session_dependency, mock_session
):
    """Тест обработки ошибки в сервисном слое (синхронная версия)."""
    # Arrange
    with patch("app.api.jellyfin.sync_jellyfin_watched_movies") as mock_sync:
        mock_sync.side_effect = Exception("Database connection failed")

        # Act
        response = await async_client.post("/api/v1/jellyfin/movies/watched")

        # Assert
        assert response.status_code == 500
        act_resp = response.json()

        exp_resp = ErrorDetail(
            message="Internal server error",
            code=JellyfinErrorCode.INTERNAL_ERROR,
        ).model_dump(mode="json", exclude_none=True)

        assert act_resp == exp_resp
        mock_sync.assert_awaited_once_with(mock_session)


@pytest.mark.asyncio
async def test_watched_movies_service_error_async(
    async_client, override_session_dependency, mock_session
):
    """Тест обработки ошибки в сервисном слое"""
    # Arrange
    with patch(
        "app.api.jellyfin.sync_jellyfin_watched_movies",
        new_callable=AsyncMock,
    ) as mock_sync:
        mock_sync.side_effect = Exception("Database connection failed")

        # Act
        response = await async_client.post("/api/v1/jellyfin/movies/watched")

        # Assert
        assert response.status_code == 500

        act_resp = response.json()
        exp_resp = ErrorDetail(
            message="Internal server error",
            code=JellyfinErrorCode.INTERNAL_ERROR,
        ).model_dump(mode="json", exclude_none=True)

        assert act_resp == exp_resp


@pytest.mark.asyncio
async def test_watched_movies_method_not_allowed(
    async_client, override_session_dependency, mock_session
):
    """Тест неподдерживаемого HTTP метода."""
    # Act
    response = await async_client.get("/api/v1/jellyfin/movies/watched")

    # Assert
    assert response.status_code == 405
    exp_resp_body = {"detail": "Method Not Allowed"}
    assert response.json() == exp_resp_body


@pytest.mark.asyncio
async def test_watched_movies_response_model(
    async_client, override_session_dependency, mock_session
):
    """Тест валидации модели ответа."""
    # Arrange
    response_data = {
        "total_users": 3,
        "total_movies_processed": 100,
        "watched_added": 15,
        "watched_updated": 8,
        "unwatched_marked": 4,
    }

    # Act
    response_model = JellyfinWatchedMoviesResponse(**response_data)

    # Assert
    assert response_model.total_users == 3
    assert response_model.total_movies_processed == 100
    assert response_model.watched_added == 15
    assert response_model.watched_updated == 8
    assert response_model.unwatched_marked == 4

    response_model_with_none = JellyfinWatchedMoviesResponse(
        total_users=0,
        total_movies_processed=0,
        watched_added=0,
        watched_updated=0,
        unwatched_marked=0,
    )
    assert response_model_with_none is not None
