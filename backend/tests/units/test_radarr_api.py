# tests/units/test_radarr_api.py
import pytest
from unittest.mock import patch, AsyncMock
from httpx import RequestError

@pytest.mark.asyncio
async def test_import_radarr_success(async_client, mock_session, radarr_movies_basic, mock_exists_result_false):
    """API должен вернуть 200 и корректный JSON при успешном импорте"""

    with patch("app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = radarr_movies_basic

        mock_session.execute.return_value = mock_exists_result_false

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "imported": len(radarr_movies_basic)}

@pytest.mark.asyncio
async def test_import_radarr_empty_success(async_client, mock_session, radarr_movies_empty, mock_exists_result_false):
    """API должен вернуть 200 и корректный JSON c 0 при получении пустого массива от radarr"""

    with patch("app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = radarr_movies_empty

        mock_session.execute.return_value = mock_exists_result_false

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "imported": len(radarr_movies_empty)}

@pytest.mark.asyncio
async def test_import_radarr_success_with_large_list(async_client, mock_session, radarr_movies_large_list, mock_exists_result_false):
    """API должен вернуть 200, количество добавленных фильмов из radarr"""

    with patch("app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = radarr_movies_large_list

        mock_session.execute.return_value = mock_exists_result_false

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "imported": len(radarr_movies_large_list)}

@pytest.mark.asyncio
async def test_import_radarr_success_with_specific_chars(async_client, mock_session, radarr_movies_special_chars, mock_exists_result_false):
    """API должен вернуть 200, количество добавленных фильмов с наличием спецсимволов из radarr"""

    with patch("app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = radarr_movies_special_chars

        mock_session.execute.return_value = mock_exists_result_false

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "imported": len(radarr_movies_special_chars)}

@pytest.mark.asyncio
async def test_import_radarr_success_with_real_data(async_client, mock_session, radarr_movies_from_json, mock_exists_result_false):
    """API должен вернуть 200, количество добавленных фильмов с неиспользуемыми полями в json из radarr"""

    with patch("app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = radarr_movies_from_json

        mock_session.execute.return_value = mock_exists_result_false

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "imported": len(radarr_movies_from_json)}

@pytest.mark.asyncio
async def test_import_radarr_skip_movie_without_radarr_id(async_client, mock_session, radarr_movies_invalid_data, mock_exists_result_false):
    """API должен вернуть 200, количество добавленных фильмов только с id radarr"""

    with patch("app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = radarr_movies_invalid_data

        mock_session.execute.return_value = mock_exists_result_false

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "imported": len(radarr_movies_invalid_data) - 1}

@pytest.mark.asyncio
async def test_import_radarr_err_on_service_failure(async_client, mock_session, mock_exists_result_false):
    """API должен вернуть 500, когда приходит ошибка из radarr"""

    with patch("app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = Exception("Service error")

        mock_session.execute.return_value = mock_exists_result_false

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 500
        assert response.json() == {'detail': 'Internal server error: Service error'}

@pytest.mark.asyncio
async def test_radarr_import_returns_network_error(async_client, mock_session, mock_exists_result_false):
    """API должен вернуть 502, когда приходит ошибка сети"""

    with patch("app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = RequestError("Network error")

        mock_session.execute.return_value = mock_exists_result_false

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 502
        assert response.json() == {'detail': 'Network error during API call: Network error'}