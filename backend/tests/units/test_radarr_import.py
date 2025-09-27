import pytest
from unittest.mock import patch, AsyncMock, MagicMock


class TestRadarrImportEndpoint:
    """Tests for endpoint /radarr/import"""

    @pytest.mark.asyncio
    async def test_radarr_import_success(self, test_app, radarr_movies_basic, mock_database_session):
        with patch('app.services.radarr_service.fetch_radarr_movies', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = radarr_movies_basic

            response = test_app.post("api/v1/radarr/import")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["imported"] == len(radarr_movies_basic)

            assert mock_database_session.execute.call_count == len(radarr_movies_basic)

    @pytest.mark.asyncio
    async def test_radarr_import_empty_list(self, test_app, radarr_movies_empty, mock_database_session):
        with patch('app.services.radarr_service.fetch_radarr_movies', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = radarr_movies_empty

            response = test_app.post("api/v1/radarr/import")

            assert response.status_code == 200
            assert response.json()["imported"] == 0

            assert mock_database_session.execute.call_count == 0

    @pytest.mark.asyncio
    async def test_radarr_import_with_duplicates(self, test_app, radarr_movies_basic, mock_database_session):
        with patch('app.services.radarr_service.fetch_radarr_movies', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = radarr_movies_basic

            mock_database_session.execute.return_value.scalar = MagicMock(
                side_effect=[True, False, False]
            )

            response = test_app.post("api/v1/radarr/import")

            assert response.status_code == 200

            assert response.json()["imported"] == 2

    @pytest.mark.asyncio
    async def test_radarr_import_many_movies(
            self, test_app, radarr_movies_from_json, mock_database_session
    ):
        with patch("app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = radarr_movies_from_json

            response = test_app.post("api/v1/radarr/import")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["imported"] == len(radarr_movies_from_json)

            assert mock_database_session.execute.call_count == len(radarr_movies_from_json)