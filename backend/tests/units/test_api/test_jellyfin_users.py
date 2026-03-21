from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import SQLAlchemyError

from app.exceptions.client_errors import ClientError
from app.schemas.error_codes import JellyfinErrorCode
from app.schemas.jellyfin import JellyfinUsersResponse
from app.schemas.responses import ErrorDetail
from app.services.jellyfin_users_service import import_jellyfin_users


@pytest.mark.asyncio
async def test_import_jellyfin_users_success(
    async_client: AsyncClient, mock_session, mock_db_result
):
    with patch(
        "app.services.jellyfin_users_service.fetch_jellyfin_users", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = [
            {"Id": "1", "Name": "Alice"},
            {"Id": "2", "Name": "Bob"},
            {"Id": "1", "Name": "Alice Updated"},
        ]

        mock_db_result.scalars.return_value.first.side_effect = [None, None, Mock(username="Alice")]

        mock_session.execute = AsyncMock(return_value=mock_db_result)

        response = await async_client.post("/api/v1/jellyfin/import/users")

        assert response.status_code == 200

        exp_res = JellyfinUsersResponse(
            status="success", imported_count=2, updated_count=1
        ).model_dump(mode="json", exclude_none=True)

        assert response.json() == exp_res


@pytest.mark.asyncio
async def test_import_jellyfin_users_client_error(async_client: AsyncClient, mock_session):
    """ClientError → 502 + JELLYFIN_NETWORK_ERROR"""
    with (
        patch.object(import_jellyfin_users, "__defaults__", (mock_session,)),
        patch(
            "app.services.jellyfin_users_service.fetch_jellyfin_users", new_callable=AsyncMock
        ) as mock_fetch,
    ):
        mock_fetch.side_effect = ClientError(
            code=JellyfinErrorCode.NETWORK_ERROR, message="Cannot reach Jellyfin"
        )

        response = await async_client.post("/api/v1/jellyfin/import/users")

        assert response.status_code == 502

        exp_resp = ErrorDetail(
            code=JellyfinErrorCode.NETWORK_ERROR, message="Cannot reach Jellyfin"
        ).model_dump(mode="json", exclude_none=True)

        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_import_jellyfin_users_db_error(
    async_client: AsyncClient, mock_session, mock_db_result
):
    """SQLAlchemyError → 500 + JELLYFIN_DATABASE_ERROR"""
    with (
        patch.object(import_jellyfin_users, "__defaults__", (mock_session,)),
        patch(
            "app.services.jellyfin_users_service.fetch_jellyfin_users", new_callable=AsyncMock
        ) as mock_fetch,
    ):
        mock_fetch.return_value = [{"Id": "1", "Name": "Alice"}]

        mock_db_result.scalars.return_value.first.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_db_result)

        mock_session.commit.side_effect = SQLAlchemyError("DB error")

        response = await async_client.post("/api/v1/jellyfin/import/users")

        assert response.status_code == 500

        exp_resp = ErrorDetail(
            code=JellyfinErrorCode.DATABASE_ERROR, message="Database operation failed"
        ).model_dump(mode="json", exclude_none=True)

        assert response.json() == exp_resp
