from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.client.radarr_client import RadarrClientError
from app.schemas.error_codes import RadarrErrorCode
from app.schemas.radarr import RadarrImportResponse
from app.schemas.responses import ErrorDetail


@pytest.mark.asyncio
async def test_import_radarr_success(
    async_client, mock_session, radarr_movies_basic, mock_exists_result_false
):
    """API должен вернуть 200 и корректный JSON при успешном импорте"""

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = radarr_movies_basic

        mock_exists_result_false.scalar.return_value = False

        mock_find_result = Mock()
        mock_find_result.scalar_one_or_none.return_value = None

        mock_session.execute.side_effect = [
            mock_exists_result_false,
            mock_find_result,
            mock_exists_result_false,
            mock_find_result,
            mock_exists_result_false,
            mock_find_result,
        ]

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 200

        exp_resp = RadarrImportResponse(
            status="success",
            imported_count=len(radarr_movies_basic),
            updated_count=0,
        ).model_dump(mode="json", exclude_none=True)

        assert response.json() == exp_resp


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

        exp_resp = RadarrImportResponse(
            status="success",
            imported_count=len(radarr_movies_empty),
            updated_count=0,
        ).model_dump(mode="json", exclude_none=True)

        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_import_radarr_success_with_large_list(
    async_client, mock_session, radarr_movies_large_list, mock_exists_result_false
):
    """API должен вернуть 200, количество добавленных фильмов из radarr"""

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = radarr_movies_large_list

        mock_exists_result_false.scalar.return_value = False

        mock_find_result = Mock()
        mock_find_result.scalar_one_or_none.return_value = None

        execute_calls = []
        for _ in radarr_movies_large_list:
            execute_calls.extend([mock_exists_result_false, mock_find_result])

        mock_session.execute.side_effect = execute_calls

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 200

        exp_resp = RadarrImportResponse(
            status="success", imported_count=len(radarr_movies_large_list), updated_count=0
        ).model_dump(mode="json", exclude_none=True)

        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_import_radarr_success_with_specific_chars(
    async_client, mock_session, radarr_movies_special_chars, mock_exists_result_false
):
    """API должен вернуть 200, количество добавленных фильмов с наличием спецсимволов из radarr"""

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = radarr_movies_special_chars

        mock_exists_result_false.scalar.return_value = False

        mock_find_result = Mock()
        mock_find_result.scalar_one_or_none.return_value = None

        execute_calls = []
        for _ in radarr_movies_special_chars:
            execute_calls.extend([mock_exists_result_false, mock_find_result])

        mock_session.execute.side_effect = execute_calls

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 200

        exp_resp = RadarrImportResponse(
            status="success", imported_count=len(radarr_movies_special_chars), updated_count=0
        ).model_dump(mode="json", exclude_none=True)

        assert response.json() == exp_resp


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

        mock_find_result = Mock()
        mock_find_result.scalar_one_or_none.return_value = None

        execute_calls = []
        for _ in radarr_movies_from_json:
            execute_calls.extend([mock_exists_result_false, mock_find_result])

        mock_session.execute.side_effect = execute_calls

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 200

        exp_resp = RadarrImportResponse(
            status="success", imported_count=len(radarr_movies_from_json), updated_count=0
        ).model_dump(mode="json", exclude_none=True)

        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_import_radarr_skip_movie_without_radarr_id(
    async_client, mock_session, radarr_movies_without_radarr_id, mock_exists_result_false
):
    """API должен вернуть 200, количество добавленных фильмов только с id radarr"""

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = radarr_movies_without_radarr_id

        mock_exists_result_false.scalar.return_value = False

        mock_find_result = Mock()
        mock_find_result.scalar_one_or_none.return_value = None

        execute_calls = []
        for movie in radarr_movies_without_radarr_id:
            if movie.get("id") is not None:
                execute_calls.append(mock_exists_result_false)
            execute_calls.append(mock_find_result)

        mock_session.execute.side_effect = execute_calls

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 200

        exp_resp = RadarrImportResponse(
            status="success",
            imported_count=len(
                [m for m in radarr_movies_without_radarr_id if m.get("id") is not None]
            ),
            updated_count=0,
        ).model_dump(mode="json", exclude_none=True)

        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_import_radarr_updates_existing_movie_by_tmdb_id(
    async_client, mock_session, existing_movie_by_tmdb_in_db
):
    """API должен обновить существующий фильм по tmdb_id, добавив radarr_id и другие данные"""
    # Arrange
    radarr_movies = [
        {
            "id": 123,
            "title": "Updated Inception Title",
            "tmdbId": 27205,
            "imdbId": "tt1375666",
            "inCinemas": "2010-07-16",
        }
    ]

    mock_exists_result = Mock()
    mock_exists_result.scalar.return_value = False

    mock_find_result = Mock()
    mock_find_result.scalar_one_or_none.return_value = existing_movie_by_tmdb_in_db

    mock_session.execute.side_effect = [
        mock_exists_result,
        mock_find_result,
    ]

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = radarr_movies

        # Act
        response = await async_client.post("/api/v1/radarr/import")

        # Assert
        assert response.status_code == 200

        exp_resp = RadarrImportResponse(
            status="success",
            imported_count=0,
            updated_count=1,
        ).model_dump(mode="json", exclude_none=True)

        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_import_radarr_updates_existing_movie_by_imdb_id(
    async_client, mock_session, existing_movie_by_imdb_in_db
):
    """API должен обновить существующий фильм по imdb_id, добавив radarr_id и tmdb_id"""
    # Arrange
    radarr_movies = [
        {
            "id": 456,
            "title": "The Matrix Reloaded",
            "tmdbId": 604,
            "imdbId": "tt0234215",
            "inCinemas": "2003-05-07",
        }
    ]

    mock_exists_result = Mock()
    mock_exists_result.scalar.return_value = False

    mock_find_result = Mock()
    mock_find_result.scalar_one_or_none.return_value = existing_movie_by_imdb_in_db

    mock_session.execute.side_effect = [
        mock_exists_result,
        mock_find_result,
    ]

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = radarr_movies

        # Act
        response = await async_client.post("/api/v1/radarr/import")

        # Assert
        assert response.status_code == 200

        exp_resp = RadarrImportResponse(
            status="success",
            imported_count=0,
            updated_count=1,
        ).model_dump(mode="json", exclude_none=True)
        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_import_radarr_without_radarr_id_updates_existing_movie(
    async_client, mock_session, existing_movie_by_tmdb_in_db
):
    """API должен обновить существующий фильм когда radarr_id=None но есть tmdb_id"""
    # Arrange
    radarr_movies = [
        {
            "id": None,
            "title": "Inception",
            "tmdbId": 27205,
            "imdbId": "tt1375666",
            "inCinemas": "2010-07-16",
        }
    ]

    mock_find_result = Mock()
    mock_find_result.scalar_one_or_none.return_value = existing_movie_by_tmdb_in_db

    mock_session.execute.return_value = mock_find_result

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = radarr_movies

        # Act
        response = await async_client.post("/api/v1/radarr/import")

        # Assert
        assert response.status_code == 200

        exp_resp = RadarrImportResponse(
            status="success",
            imported_count=0,
            updated_count=1,
        ).model_dump(mode="json", exclude_none=True)

        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_import_radarr_skips_update_when_movie_already_complete(
    async_client, mock_session, existing_movie_complete
):
    """API должен пропустить обновление когда все данные уже заполнены"""
    # Arrange
    radarr_movies = [
        {
            "id": 123,
            "title": "Inception",
            "tmdbId": 27205,
            "imdbId": "tt1375666",
            "inCinemas": "2010-07-16",
        }
    ]

    mock_exists_result = Mock()
    mock_exists_result.scalar.return_value = False

    mock_find_result = Mock()
    mock_find_result.scalar_one_or_none.return_value = existing_movie_complete

    mock_session.execute.side_effect = [
        mock_exists_result,
        mock_find_result,
    ]

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = radarr_movies

        # Act
        response = await async_client.post("/api/v1/radarr/import")

        # Assert
        assert response.status_code == 200

        exp_resp = RadarrImportResponse(
            status="success", imported_count=0, updated_count=0
        ).model_dump(mode="json", exclude_none=True)

        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_import_radarr_creates_new_when_no_external_ids_match(
    async_client, mock_session, mock_exists_result_false
):
    """API должен создать новый фильм когда нет совпадений по external_ids"""
    # Arrange
    radarr_movies = [
        {
            "id": 999,
            "title": "Brand New Movie",
            "tmdbId": 99999,
            "imdbId": "tt9999999",
            "inCinemas": "2024-01-01",
        }
    ]

    mock_exists_result_false.scalar.return_value = False

    mock_find_result = Mock()
    mock_find_result.scalar_one_or_none.return_value = None

    mock_session.execute.side_effect = [
        mock_exists_result_false,
        mock_find_result,
    ]

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = radarr_movies

        # Act
        response = await async_client.post("/api/v1/radarr/import")

        # Assert
        assert response.status_code == 200

        exp_resp = RadarrImportResponse(
            status="success",
            imported_count=1,
            updated_count=0,
        ).model_dump(mode="json", exclude_none=True)
        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_import_radarr_skips_movie_without_any_ids(async_client, mock_session):
    """API должен пропустить фильм без каких-либо идентификаторов"""
    # Arrange
    radarr_movies = [
        {
            "id": None,
            "title": "Movie Without IDs",
            "tmdbId": None,
            "imdbId": None,
            "inCinemas": None,
        }
    ]

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = radarr_movies

        # Act
        response = await async_client.post("/api/v1/radarr/import")

        # Assert
        assert response.status_code == 200

        exp_resp = RadarrImportResponse(
            status="success", imported_count=0, updated_count=0
        ).model_dump(mode="json", exclude_none=True)

        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_import_radarr_mixed_scenarios(
    async_client, mock_session, existing_movie_by_tmdb_in_db, mock_exists_result_false
):
    """API должен корректно обработать смешанный сценарий: обновление + создание"""
    # Arrange
    radarr_movies = [
        {
            "id": 123,
            "title": "Inception Updated",
            "tmdbId": 27205,
            "imdbId": "tt1375666",
            "inCinemas": "2010-07-16",
        },
        {
            "id": 456,
            "title": "New Movie",
            "tmdbId": 11111,
            "imdbId": "tt1111111",
            "inCinemas": "2024-01-01",
        },
        {"id": None, "title": "No ID Movie", "tmdbId": None, "imdbId": None, "inCinemas": None},
    ]

    mock_exists_123 = Mock()
    mock_exists_123.scalar.return_value = False

    mock_exists_456 = Mock()
    mock_exists_456.scalar.return_value = False

    mock_find_existing = Mock()
    mock_find_existing.scalar_one_or_none.return_value = existing_movie_by_tmdb_in_db

    mock_find_none = Mock()
    mock_find_none.scalar_one_or_none.return_value = None

    mock_session.execute.side_effect = [
        mock_exists_123,
        mock_find_existing,
        mock_exists_456,
        mock_find_none,
        mock_find_none,
    ]

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = radarr_movies

        # Act
        response = await async_client.post("/api/v1/radarr/import")

        # Assert
        assert response.status_code == 200

        exp_resp = RadarrImportResponse(
            status="success",
            imported_count=1,
            updated_count=1,
        ).model_dump(mode="json", exclude_none=True)

        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_import_radarr_skip_movie_with_invalid_data(
    async_client, mock_session, radarr_movies_invalid_data, mock_exists_result_false
):
    """API должен вернуть 200, добавляются все фильмы, в том числе с невалидной датой"""

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = radarr_movies_invalid_data

        mock_exists_result_false.scalar.return_value = False

        mock_find_result = Mock()
        mock_find_result.scalar_one_or_none.return_value = None

        execute_calls = []
        for movie in radarr_movies_invalid_data:
            if movie.get("id") is not None:
                execute_calls.append(mock_exists_result_false)
            execute_calls.append(mock_find_result)

        mock_session.execute.side_effect = execute_calls

        response = await async_client.post("/api/v1/radarr/import")

        assert response.status_code == 200

        exp_resp = RadarrImportResponse(
            status="success", imported_count=2, updated_count=0
        ).model_dump(mode="json", exclude_none=True)

        assert response.json() == exp_resp


@pytest.mark.asyncio()
async def test_import_radarr_err_on_service_failure(
    async_client, mock_session, mock_exists_result_false
):
    """API должен вернуть 400 с ошибкой в ответе, когда приходит ошибка из radarr"""
    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.side_effect = RadarrClientError(
            code=RadarrErrorCode.FETCH_FAILED, message="Service error"
        )
        mock_session.execute.return_value = mock_exists_result_false
        response = await async_client.post("/api/v1/radarr/import")
        assert response.status_code == 400

        exp_resp = ErrorDetail(
            code=RadarrErrorCode.FETCH_FAILED, message="Service error"
        ).model_dump(mode="json", exclude_none=True)
        assert response.json() == exp_resp


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

        exp_resp = ErrorDetail(
            code=RadarrErrorCode.NETWORK_ERROR, message="Failed to connect to external service"
        ).model_dump(mode="json", exclude_none=True)

        assert response.json() == exp_resp
