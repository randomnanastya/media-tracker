from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.database import get_session
from app.main import app
from app.schemas.error_codes import JellyfinErrorCode
from app.schemas.jellyfin import JellyfinWatchedSeriesResponse
from app.schemas.responses import ErrorDetail


class TestJellyfinWatchedSeriesAPI:
    """Тесты для API синхронизации просмотренных сериалов из Jellyfin."""

    @pytest.fixture
    def mock_session(self):
        """Мок асинхронной сессии базы данных."""
        session = AsyncMock()

        mock_scalars = AsyncMock()
        mock_scalars.all.return_value = []

        mock_result = AsyncMock()
        mock_result.scalars.return_value = mock_scalars

        session.execute.return_value = mock_result
        session.commit = AsyncMock()
        session.rollback = AsyncMock()

        return session

    @pytest.fixture
    def client(self, mock_session):
        """Синхронный тестовый клиент."""

        def override_get_session():
            return mock_session

        app.dependency_overrides = {get_session: override_get_session}

        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client

        app.dependency_overrides.clear()

    @pytest.fixture
    async def async_client(self, mock_session):
        """Асинхронный тестовый клиент."""

        async def override_get_session():
            return mock_session

        app.dependency_overrides = {get_session: override_get_session}

        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_watched_series_success(async_client, override_session_dependency, mock_session):
    """Тест успешной синхронизации сериалов."""
    # Arrange
    mock_response = JellyfinWatchedSeriesResponse(
        total_users=3,
        total_episodes_processed=200,
        watched_added=25,
        watched_updated=12,
        unwatched_marked=6,
    )

    with (
        patch(
            "app.api.jellyfin.sync_jellyfin_watched_series",
            new_callable=AsyncMock,
        ) as mock_sync,
        patch(
            "app.services.sync_jellyfin_watched_series_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://jellyfin:8096", "test-api-key"),
        ),
    ):
        mock_sync.return_value = mock_response

        # Act
        response = await async_client.post("/api/v1/jellyfin/series/watched")

        # Assert
        assert response.status_code == 200
        assert response.json() == mock_response.model_dump(mode="json", exclude_none=True)

        mock_sync.assert_awaited_once_with(mock_session)


@pytest.mark.asyncio
async def test_watched_series_empty_result(async_client, override_session_dependency, mock_session):
    """Тест пустого результата."""
    # Arrange
    mock_response = JellyfinWatchedSeriesResponse(
        total_users=0,
        total_episodes_processed=0,
        watched_added=0,
        watched_updated=0,
        unwatched_marked=0,
    )

    with (
        patch(
            "app.api.jellyfin.sync_jellyfin_watched_series",
            new_callable=AsyncMock,
        ) as mock_sync,
        patch(
            "app.services.sync_jellyfin_watched_series_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://jellyfin:8096", "test-api-key"),
        ),
    ):
        mock_sync.return_value = mock_response

        # Act
        act_resp = await async_client.post("/api/v1/jellyfin/series/watched")

        # Assert
        assert act_resp.status_code == 200
        assert act_resp.json() == mock_response.model_dump(mode="json", exclude_none=True)

        mock_sync.assert_awaited_once_with(mock_session)


@pytest.mark.asyncio
async def test_watched_series_service_error_async(
    async_client, override_session_dependency, mock_session
):
    """Ошибка в сервисном слое (async)."""
    with (
        patch(
            "app.api.jellyfin.sync_jellyfin_watched_series",
            new_callable=AsyncMock,
        ) as mock_sync,
        patch(
            "app.services.sync_jellyfin_watched_series_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://jellyfin:8096", "test-api-key"),
        ),
    ):
        # Arrange
        mock_sync.side_effect = Exception("Database connection failed")

        # Act
        act_resp = await async_client.post("/api/v1/jellyfin/series/watched")

        # Assert
        assert act_resp.status_code == 500
        assert act_resp.json() == ErrorDetail(
            message="Internal server error",
            code=JellyfinErrorCode.INTERNAL_ERROR,
        ).model_dump(mode="json", exclude_none=True)


@pytest.mark.asyncio
async def test_watched_series_method_not_allowed(
    async_client, override_session_dependency, mock_session
):
    """Неподдерживаемый HTTP метод."""
    with patch(
        "app.services.sync_jellyfin_watched_series_service.get_decrypted_config",
        new_callable=AsyncMock,
        return_value=("http://jellyfin:8096", "test-api-key"),
    ):
        # Act
        act_resp = await async_client.get("/api/v1/jellyfin/series/watched")

        # Assert
        assert act_resp.status_code == 405
        assert act_resp.json() == {"detail": "Method Not Allowed"}


@pytest.mark.asyncio
async def test_watched_series_response_model():
    """Валидация модели ответа."""
    response = JellyfinWatchedSeriesResponse(
        total_users=2,
        total_episodes_processed=150,
        watched_added=20,
        watched_updated=10,
        unwatched_marked=5,
    )

    assert response.total_users == 2
    assert response.total_episodes_processed == 150

    response_min = JellyfinWatchedSeriesResponse(
        total_users=0,
        total_episodes_processed=0,
        watched_added=0,
        watched_updated=0,
        unwatched_marked=0,
    )

    assert response_min.total_users == 0
