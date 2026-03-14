from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.schemas.error_codes import AuthErrorCode
from tests.factories import AppUserFactory


@pytest.mark.asyncio
async def test_get_status_setup_required(async_client: AsyncClient) -> None:
    with patch("app.api.auth.auth_service.is_setup_required", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = True
        response = await async_client.get("/api/v1/auth/status")
    assert response.status_code == 200
    assert response.json() == {"setup_required": True}


@pytest.mark.asyncio
async def test_get_status_setup_not_required(async_client: AsyncClient) -> None:
    with patch("app.api.auth.auth_service.is_setup_required", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = False
        response = await async_client.get("/api/v1/auth/status")
    assert response.status_code == 200
    assert response.json() == {"setup_required": False}


@pytest.mark.asyncio
async def test_register_success(async_client: AsyncClient) -> None:
    user = AppUserFactory.build(username="newuser")
    with patch("app.api.auth.auth_service.register_user", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = (user, "AAAAA-BBBBB-CCCCC-DDDDD")
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"username": "newuser", "password": "pass1234"},
        )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["recovery_code"] == "AAAAA-BBBBB-CCCCC-DDDDD"


@pytest.mark.asyncio
async def test_register_closed(async_client: AsyncClient) -> None:
    with patch("app.api.auth.auth_service.register_user", new_callable=AsyncMock) as mock_fn:
        mock_fn.side_effect = HTTPException(403, detail={"code": AuthErrorCode.REGISTRATION_CLOSED})
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"username": "user", "password": "pass1234"},
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient) -> None:
    user = AppUserFactory.build(id=1)
    with patch("app.api.auth.auth_service.authenticate_user", new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value = user
        with patch(
            "app.api.auth.auth_service.create_refresh_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_refresh.return_value = "raw-refresh-token"
            with (
                patch("app.api.auth.create_access_token", return_value="access-token-123"),
                patch.dict(
                    "os.environ",
                    {
                        "JWT_SECRET": "secret",
                        "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
                        "REFRESH_TOKEN_EXPIRE_DAYS": "30",
                    },
                ),
            ):
                response = await async_client.post(
                    "/api/v1/auth/login",
                    json={"username": "user", "password": "pass"},
                )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data


@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client: AsyncClient) -> None:
    with patch("app.api.auth.auth_service.authenticate_user", new_callable=AsyncMock) as mock_fn:
        mock_fn.side_effect = HTTPException(401, detail={"code": AuthErrorCode.INVALID_CREDENTIALS})
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "user", "password": "wrong"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_success(async_client: AsyncClient) -> None:
    with patch("app.api.auth.auth_service.refresh_access_token", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = ("new-access", "new-refresh")
        with patch.dict(
            "os.environ",
            {"JWT_SECRET": "secret", "ACCESS_TOKEN_EXPIRE_MINUTES": "15"},
        ):
            response = await async_client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "old-refresh-token"},
            )
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "new-access"
    assert data["refresh_token"] == "new-refresh"


@pytest.mark.asyncio
async def test_logout_success(async_client: AsyncClient) -> None:
    with patch("app.api.auth.auth_service.revoke_refresh_token", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = None
        response = await async_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": "some-token"},
        )
    assert response.status_code == 200
    assert response.json() == {"message": "ok"}


@pytest.mark.asyncio
async def test_get_me(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testadmin"
    assert data["id"] == 1


@pytest.mark.asyncio
async def test_put_me(async_client: AsyncClient) -> None:
    updated_user = AppUserFactory.build(id=1, username="updated_name")
    with patch("app.api.auth.auth_service.update_user_profile", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = updated_user
        response = await async_client.put(
            "/api/v1/auth/me",
            json={"username": "updated_name"},
        )
    assert response.status_code == 200
    assert response.json()["username"] == "updated_name"


@pytest.mark.asyncio
async def test_change_password_success(async_client: AsyncClient) -> None:
    with patch("app.api.auth.auth_service.change_password", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = None
        response = await async_client.put(
            "/api/v1/auth/me/password",
            json={"current_password": "oldpass", "new_password": "newpass123"},
        )
    assert response.status_code == 200
    assert response.json() == {"message": "ok"}


@pytest.mark.asyncio
async def test_get_recovery_code(async_client: AsyncClient) -> None:
    with patch(
        "app.api.auth.auth_service.regenerate_recovery_code", new_callable=AsyncMock
    ) as mock_fn:
        mock_fn.return_value = "AAAAA-BBBBB-CCCCC-DDDDD"
        response = await async_client.get("/api/v1/auth/recovery-code")
    assert response.status_code == 200
    assert response.json()["recovery_code"] == "AAAAA-BBBBB-CCCCC-DDDDD"


# === POST /reset-password ===


@pytest.mark.asyncio
async def test_reset_password_success(async_client: AsyncClient) -> None:
    user = AppUserFactory.build()
    with patch(
        "app.api.auth.auth_service.reset_password_with_code", new_callable=AsyncMock
    ) as mock_fn:
        mock_fn.return_value = (user, "NEW-CODE-XXXX-YYYY")
        response = await async_client.post(
            "/api/v1/auth/reset-password",
            json={"recovery_code": "AAAAA-BBBBB-CCCCC-DDDDD", "new_password": "newpass123"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "new_recovery_code" in data
    assert "message" in data
    assert data["new_recovery_code"] == "NEW-CODE-XXXX-YYYY"


@pytest.mark.asyncio
async def test_reset_password_invalid_code(async_client: AsyncClient) -> None:
    with patch(
        "app.api.auth.auth_service.reset_password_with_code", new_callable=AsyncMock
    ) as mock_fn:
        mock_fn.side_effect = HTTPException(400, detail={"code": "INVALID_RECOVERY_CODE"})
        response = await async_client.post(
            "/api/v1/auth/reset-password",
            json={"recovery_code": "WRONG-CODE-XXXX-YYYY", "new_password": "newpass123"},
        )
    assert response.status_code == 400


# === Валидация ===


@pytest.mark.asyncio
async def test_register_validation_too_short(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"username": "ab", "password": "pass1234"},
    )
    assert response.status_code == 422


# === PUT /me конфликт ===


@pytest.mark.asyncio
async def test_update_me_username_taken(async_client: AsyncClient) -> None:
    with patch("app.api.auth.auth_service.update_user_profile", new_callable=AsyncMock) as mock_fn:
        mock_fn.side_effect = HTTPException(409, detail={"code": "USERNAME_TAKEN"})
        response = await async_client.put(
            "/api/v1/auth/me",
            json={"username": "taken_name"},
        )
    assert response.status_code == 409


# === PUT /me/password ошибка ===


@pytest.mark.asyncio
async def test_change_password_wrong_current(async_client: AsyncClient) -> None:
    with patch("app.api.auth.auth_service.change_password", new_callable=AsyncMock) as mock_fn:
        mock_fn.side_effect = HTTPException(400, detail={"code": "INVALID_CREDENTIALS"})
        response = await async_client.put(
            "/api/v1/auth/me/password",
            json={"current_password": "wrongpass", "new_password": "newpass123"},
        )
    assert response.status_code == 400
