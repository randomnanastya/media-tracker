"""Unit tests for GET /api/v1/users endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.factories import UserFactory


@pytest.mark.asyncio
async def test_list_users_returns_empty_list(async_client: AsyncClient) -> None:
    """Сервис возвращает [], ответ 200 с пустым списком."""
    with patch("app.api.users.users_service.get_jellyfin_users", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = []
        response = await async_client.get("/api/v1/users")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_users_returns_users(async_client: AsyncClient) -> None:
    """Сервис возвращает 2 пользователей — ответ содержит их поля."""
    user1 = UserFactory.build(id=1, username="alice", jellyfin_user_id="jf-alice-uuid")
    user2 = UserFactory.build(id=2, username="bob", jellyfin_user_id="jf-bob-uuid")

    with patch("app.api.users.users_service.get_jellyfin_users", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = [user1, user2]
        response = await async_client.get("/api/v1/users")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    assert data[0]["id"] == 1
    assert data[0]["username"] == "alice"
    assert data[0]["jellyfin_user_id"] == "jf-alice-uuid"

    assert data[1]["id"] == 2
    assert data[1]["username"] == "bob"
    assert data[1]["jellyfin_user_id"] == "jf-bob-uuid"


@pytest.mark.asyncio
async def test_list_users_user_without_jellyfin_id(async_client: AsyncClient) -> None:
    """Пользователь с jellyfin_user_id=None — в ответе jellyfin_user_id: null."""
    user = UserFactory.build(id=5, username="no_jf_user", jellyfin_user_id=None)

    with patch("app.api.users.users_service.get_jellyfin_users", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = [user]
        response = await async_client.get("/api/v1/users")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["jellyfin_user_id"] is None


@pytest.mark.asyncio
async def test_list_users_requires_auth(async_client: AsyncClient) -> None:
    """Без токена запрос должен вернуть 401.

    Для этого теста убираем override аутентификации, который выставлен autouse=True.
    Используем отдельный клиент без dependency override auth.
    """
    from fastapi import HTTPException

    from app.dependencies.auth import get_current_user
    from app.main import app

    # Временно заменяем auth dependency на реальный (вызывающий 401)
    async def raise_401() -> None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    app.dependency_overrides[get_current_user] = raise_401
    try:
        response = await async_client.get("/api/v1/users")
    finally:
        # Убираем наш override — autouse-фикстура восстановит свой при следующем тесте
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 401
