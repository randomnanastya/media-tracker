from unittest.mock import AsyncMock, patch

import httpx
import pytest


@pytest.mark.asyncio
async def test_import_radarr_success(
    async_client, mock_session, radarr_movies_basic, mock_exists_result_false
):
    """API должен вернуть 200 и корректный JSON при успешном импорте"""

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = radarr_movies_basic

        mock_session.execute.return_value = mock_exists_result_false

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "imported_count": len(radarr_movies_basic),
            "error": None,
        }


@pytest.mark.asyncio
async def test_import_radarr_empty_success(
    async_client, mock_session, radarr_movies_empty, mock_exists_result_false
):
    """API должен вернуть 200 и корректный JSON c 0 при получении пустого массива от radarr"""

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = radarr_movies_empty

        mock_session.execute.return_value = mock_exists_result_false

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "imported_count": len(radarr_movies_empty),
            "error": None,
        }


@pytest.mark.asyncio
async def test_import_radarr_success_with_large_list(
    async_client, mock_session, radarr_movies_large_list, mock_exists_result_false
):
    """API должен вернуть 200, количество добавленных фильмов из radarr"""

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = radarr_movies_large_list

        mock_session.execute.return_value = mock_exists_result_false

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "imported_count": len(radarr_movies_large_list),
            "error": None,
        }


@pytest.mark.asyncio
async def test_import_radarr_success_with_specific_chars(
    async_client, mock_session, radarr_movies_special_chars, mock_exists_result_false
):
    """API должен вернуть 200, количество добавленных фильмов с наличием спецсимволов из radarr"""

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = radarr_movies_special_chars

        mock_session.execute.return_value = mock_exists_result_false

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "imported_count": len(radarr_movies_special_chars),
            "error": None,
        }


@pytest.mark.asyncio
async def test_import_radarr_success_with_real_data(
    async_client, mock_session, radarr_movies_from_json, mock_exists_result_false
):
    """API должен вернуть 200, количество добавленных фильмов с неиспользуемыми полями в json из radarr"""

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = radarr_movies_from_json

        mock_session.execute.return_value = mock_exists_result_false

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "imported_count": len(radarr_movies_from_json),
            "error": None,
        }


@pytest.mark.asyncio
async def test_import_radarr_skip_movie_without_radarr_id(
    async_client, mock_session, radarr_movies_without_radarr_id, mock_exists_result_false
):
    """API должен вернуть 200, количество добавленных фильмов только с id radarr"""

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = radarr_movies_without_radarr_id

        mock_session.execute.return_value = mock_exists_result_false

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "imported_count": len(radarr_movies_without_radarr_id) - 1,
            "error": None,
        }


@pytest.mark.asyncio
async def test_import_radarr_skip_movie_with_invalid_data(
    async_client, mock_session, radarr_movies_invalid_data, mock_exists_result_false
):
    """API должен вернуть 200, количество добавленных фильмов с валидной датой"""

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = radarr_movies_invalid_data

        mock_session.execute.return_value = mock_exists_result_false

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "imported_count": len(radarr_movies_invalid_data) - 1,
            "error": None,
        }


@pytest.mark.asyncio()
async def test_import_radarr_err_on_service_failure(
    async_client, mock_session, mock_exists_result_false
):
    """API должен вернуть 500 с ошибкой в ответе, когда приходит ошибка из radarr"""
    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.side_effect = Exception("Service error")
        mock_session.execute.return_value = mock_exists_result_false
        response = await async_client.post("/api/v1/radarr/import")
        assert response.status_code == 500
        assert response.json() == {
            "detail": {"code": "RADARR_FETCH_FAILED", "message": "Network error: Service error"}
        }


@pytest.mark.asyncio
async def test_radarr_import_returns_network_error(
    async_client, mock_session, mock_exists_result_false
):
    """API должен вернуть 502 с ошибкой сети в ответе"""
    fake_request = httpx.Request("GET", "http://testserver")
    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.side_effect = httpx.RequestError("Network error", request=fake_request)
        mock_session.execute.return_value = mock_exists_result_false
        response = await async_client.post("/api/v1/radarr/import")
        assert response.status_code == 502
        assert response.json() == {
            "detail": {
                "code": "NETWORK_ERROR",
                "message": "Network error: Network error",
            },
        }
