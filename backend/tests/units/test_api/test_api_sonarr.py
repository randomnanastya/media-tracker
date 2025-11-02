from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import SQLAlchemyError

from app.exceptions.client_errors import ClientError
from app.schemas.error_codes import SonarrErrorCode
from app.schemas.responses import ErrorDetail
from app.schemas.sonarr import SonarrImportResponse


@pytest.mark.asyncio
async def test_import_sonarr_success(
    async_client, mock_session, sonarr_series_basic, sonarr_episodes_basic, mock_exists_result_false
):
    """Test Sonarr import endpoint returns success response."""
    with (
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_fetch_series,
        patch(
            "app.services.sonarr_service.fetch_sonarr_episodes", new_callable=AsyncMock
        ) as mock_fetch_episodes,
    ):
        mock_fetch_series.return_value = sonarr_series_basic

        mock_fetch_episodes.side_effect = [
            sonarr_episodes_basic if series_id == 1 else []
            for series_id in [s["id"] for s in sonarr_series_basic]
        ]
        mock_session.execute.return_value = mock_exists_result_false
        mock_session.scalar.return_value = None

        response = await async_client.post("/api/v1/sonarr/import")

        assert response.status_code == 200

        exp_resp = SonarrImportResponse(
            new_series=len(sonarr_series_basic),
            updated_series=0,
            new_episodes=len(sonarr_episodes_basic),
            updated_episodes=0,
        ).model_dump(mode="json", exclude_none=True)
        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_import_sonarr_db_commit_failure(
    async_client, override_session_dependency, mock_session
):
    """API должен вернуть 500 при ошибке в session.commit()."""

    mock_session.commit = AsyncMock(side_effect=SQLAlchemyError("DB commit failed"))
    mock_session.rollback = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.scalar = AsyncMock(return_value=None)
    mock_session.add = MagicMock()

    with (
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_series,
        patch(
            "app.services.sonarr_service.fetch_sonarr_episodes", new_callable=AsyncMock
        ) as mock_eps,
    ):

        mock_series.return_value = [
            {
                "id": 1,
                "title": "Test series",
                "year": 2024,
                "images": [],
                "ratings": {},
                "genres": [],
            }
        ]
        mock_eps.return_value = []

        response = await async_client.post("/api/v1/sonarr/import")

    assert response.status_code == 500

    exp_res = ErrorDetail(
        code=SonarrErrorCode.DATABASE_ERROR, message="Database operation failed"
    ).model_dump(mode="json", exclude_none=True)
    assert response.json() == exp_res


@pytest.mark.asyncio
async def test_sonarr_import_endpoint_error(async_client: AsyncClient):
    with patch(
        "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.side_effect = ClientError(
            code=SonarrErrorCode.FETCH_FAILED, message="Network error"
        )

        response = await async_client.post("/api/v1/sonarr/import")
        assert response.status_code == 400

        exp_resp = ErrorDetail(
            code=SonarrErrorCode.FETCH_FAILED, message="Network error"
        ).model_dump(mode="json", exclude_none=True)

        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_sonarr_import_endpoint_no_api_key(async_client: AsyncClient):
    """Test Sonarr import endpoint when SONARR_API_KEY is not set."""
    with patch("app.client.sonarr_client.SONARR_API_KEY", None):
        response = await async_client.post("/api/v1/sonarr/import")
        assert response.status_code == 400
        assert response.json() == {
            "code": SonarrErrorCode.INTERNAL_ERROR,
            "message": "Sonarr API key is not configured",
        }
