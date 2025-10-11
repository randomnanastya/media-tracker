# tests/units/test_radarr_api.py
import pytest
from unittest.mock import patch, AsyncMock, Mock
from httpx import AsyncClient, RequestError

from app.main import app
from app.database import get_session


@pytest.mark.asyncio
async def test_import_radarr_success(radarr_movies_basic):
    mock_session = AsyncMock()

    with patch("app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = radarr_movies_basic

        mock_result = Mock()
        mock_result.scalar.return_value = False
        mock_session.execute.return_value = mock_result

        # # Override the session dependency
        async def override_get_session():
            return mock_session

        app.dependency_overrides[get_session] = override_get_session

        # Call the endpoint using AsyncClient
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/api/v1/radarr/import")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "imported": 3}

    # # Clean up overrides
    app.dependency_overrides = {}


# @pytest.mark.asyncio
# async def test_radarr_import_returns_success(radarr_movies_basic):
#     """Test API returns success response on successful import"""
#
#     # Arrange
#     with patch("app.services.radarr_service.import_radarr_movies", new_callable=AsyncMock) as mock_service:
#         mock_service.return_value = 3  # Сервис вернул что импортировал 3 фильма
#         # Mock session (нужен для dependency)
#         mock_session = AsyncMock()
#
#         async def override_get_session():
#             return mock_session
#
#         app.dependency_overrides[get_session] = override_get_session
#
#         # Act
#         async with AsyncClient(app=app, base_url="http://test") as ac:
#             response = await ac.post("/api/v1/radarr/import")
#
#         # Assert - проверяем только HTTP ответ
#         assert response.status_code == 200
#         assert response.json() == {"status": "ok", "imported": 3}
#
#         # Проверяем что сервис был вызван
#         mock_service.assert_called_once()
#
#     # Clean up
#     app.dependency_overrides = {}
#
#
# @pytest.mark.asyncio
# async def test_radarr_import_returns_error_on_service_failure():
#     """Test API returns error when service fails"""
#     # Arrange
#     with patch("app.services.radarr_service.import_radarr_movies", new_callable=AsyncMock) as mock_service:
#         mock_service.side_effect = Exception("Service error")
#
#         # Mock session
#         mock_session = AsyncMock()
#
#         async def override_get_session():
#             return mock_session
#
#         app.dependency_overrides[get_session] = override_get_session
#
#         # Act
#         async with AsyncClient(app=app, base_url="http://test") as ac:
#             response = await ac.post("/api/v1/radarr/import")
#
#         # Assert - проверяем обработку ошибок
#         assert response.status_code == 500
#         assert "error" in response.json()
#
#         mock_service.assert_called_once()
#
#     # Clean up
#     app.dependency_overrides = {}
#
#
# @pytest.mark.asyncio
# async def test_radarr_import_returns_network_error():
#     """Test API returns network error when Radarr API fails"""
#     # Arrange
#     with patch("app.services.radarr_service.import_radarr_movies", new_callable=AsyncMock) as mock_service:
#         mock_service.side_effect = RequestError("Network error")
#
#         # Mock session
#         mock_session = AsyncMock()
#
#         async def override_get_session():
#             return mock_session
#
#         app.dependency_overrides[get_session] = override_get_session
#
#         # Act
#         async with AsyncClient(app=app, base_url="http://test") as ac:
#             response = await ac.post("/api/v1/radarr/import")
#
#         # Assert
#         assert response.status_code == 502
#         assert "Network error" in response.json().get("detail", "")
#
#         mock_service.assert_called_once()
#
#     # Clean up
#     app.dependency_overrides = {}
#
#