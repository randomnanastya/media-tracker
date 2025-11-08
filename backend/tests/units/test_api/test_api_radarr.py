from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.client.radarr_client import RadarrClientError
from app.schemas.error_codes import RadarrErrorCode
from app.schemas.radarr import RadarrImportResponse
from app.schemas.responses import ErrorDetail


@pytest.mark.asyncio
async def test_import_radarr_success_basic(async_client, radarr_movies_basic):
    """API должен вернуть 200 при успешном импорте базовых данных"""
    with patch("app.api.radarr.import_radarr_movies", new_callable=AsyncMock) as mock_import:
        mock_import.return_value = RadarrImportResponse(
            status="success",
            imported_count=len(radarr_movies_basic),
            updated_count=0,
        )

        response = await async_client.post("/api/v1/radarr/import")
        assert response.status_code == 200

        exp_resp = RadarrImportResponse(
            status="success",
            imported_count=len(radarr_movies_basic),
            updated_count=0,
        ).model_dump(mode="json", exclude_none=True)
        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_import_radarr_success_complex_cases(
    async_client, radarr_movies_large_list, radarr_movies_special_chars
):
    """API должен вернуть 200 для сложных случаев: большие списки и спецсимволы"""
    with patch("app.api.radarr.import_radarr_movies", new_callable=AsyncMock) as mock_import:
        # Тестируем большой список
        mock_import.return_value = RadarrImportResponse(
            status="success", imported_count=len(radarr_movies_large_list), updated_count=0
        )

        response = await async_client.post("/api/v1/radarr/import")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_import_radarr_empty_success(async_client, radarr_movies_empty):
    """API должен вернуть 200 при пустом массиве от radarr"""
    with patch("app.api.radarr.import_radarr_movies", new_callable=AsyncMock) as mock_import:
        mock_import.return_value = RadarrImportResponse(
            status="success",
            imported_count=0,
            updated_count=0,
        )

        response = await async_client.post("/api/v1/radarr/import")
        assert response.status_code == 200

        exp_resp = RadarrImportResponse(
            status="success",
            imported_count=0,
            updated_count=0,
        ).model_dump(mode="json", exclude_none=True)
        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_import_radarr_updates_existing_movies(async_client):
    """API должен обновлять существующие фильмы по разным идентификаторам"""
    with patch("app.api.radarr.import_radarr_movies", new_callable=AsyncMock) as mock_import:
        mock_import.return_value = RadarrImportResponse(
            status="success",
            imported_count=0,
            updated_count=2,  # Обновили 2 фильма
        )

        response = await async_client.post("/api/v1/radarr/import")
        assert response.status_code == 200

        exp_resp = RadarrImportResponse(
            status="success",
            imported_count=0,
            updated_count=2,
        ).model_dump(mode="json", exclude_none=True)
        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_import_radarr_skips_invalid_movies(
    async_client, radarr_movies_without_radarr_id, radarr_movies_invalid_data
):
    """API должен пропускать фильмы без ID или с невалидными данными"""
    with patch("app.api.radarr.import_radarr_movies", new_callable=AsyncMock) as mock_import:
        # Пропускаем фильмы без radarr_id (только 1 валидный из 2)
        valid_count = len([m for m in radarr_movies_without_radarr_id if m.get("id") is not None])

        mock_import.return_value = RadarrImportResponse(
            status="success",
            imported_count=valid_count,
            updated_count=0,
        )

        response = await async_client.post("/api/v1/radarr/import")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_import_radarr_mixed_scenario(async_client):
    """API должен корректно обработать смешанный сценарий: создание + обновление + пропуск"""
    with patch("app.api.radarr.import_radarr_movies", new_callable=AsyncMock) as mock_import:
        mock_import.return_value = RadarrImportResponse(
            status="success",
            imported_count=2,  # Создали 2 новых
            updated_count=1,  # Обновили 1 существующий
        )

        response = await async_client.post("/api/v1/radarr/import")
        assert response.status_code == 200

        exp_resp = RadarrImportResponse(
            status="success",
            imported_count=2,
            updated_count=1,
        ).model_dump(mode="json", exclude_none=True)
        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_import_radarr_service_error(async_client):
    """API должен вернуть 400 при ошибке сервиса Radarr"""
    with patch("app.api.radarr.import_radarr_movies", new_callable=AsyncMock) as mock_import:
        mock_import.side_effect = RadarrClientError(
            code=RadarrErrorCode.FETCH_FAILED, message="Service error"
        )

        response = await async_client.post("/api/v1/radarr/import")
        assert response.status_code == 400

        exp_resp = ErrorDetail(
            code=RadarrErrorCode.FETCH_FAILED, message="Service error"
        ).model_dump(mode="json", exclude_none=True)
        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_import_radarr_network_error(async_client):
    """API должен вернуть 502 при сетевой ошибке"""
    with patch("app.api.radarr.import_radarr_movies", new_callable=AsyncMock) as mock_import:
        mock_import.side_effect = httpx.RequestError("Network error", request=None)

        response = await async_client.post("/api/v1/radarr/import")
        assert response.status_code == 502

        exp_resp = ErrorDetail(
            code=RadarrErrorCode.NETWORK_ERROR, message="Failed to connect to external service"
        ).model_dump(mode="json", exclude_none=True)
        assert response.json() == exp_resp
