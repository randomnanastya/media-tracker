"""Unit tests for /api/v1/settings/services endpoints (no real DB)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.models import ServiceConfig, ServiceType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(service_type: ServiceType, url: str, encrypted_key: str) -> ServiceConfig:
    cfg = ServiceConfig.__new__(ServiceConfig)
    cfg.id = 1
    cfg.service_type = service_type
    cfg.url = url
    cfg.encrypted_api_key = encrypted_key
    return cfg


# ---------------------------------------------------------------------------
# GET /api/v1/settings/services
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_services_empty_db(async_client, mock_session):
    """Empty DB → all 3 services returned with is_configured=False."""
    with patch(
        "app.api.settings.config_repo.get_all_configs",
        new_callable=AsyncMock,
        return_value=[],
    ):
        response = await async_client.get("/api/v1/settings/services")

    assert response.status_code == 200
    data = response.json()
    assert "services" in data
    assert len(data["services"]) == 3
    for svc in data["services"]:
        assert svc["is_configured"] is False
        assert svc["url"] == ""
        assert svc["masked_api_key"] == ""


@pytest.mark.asyncio
async def test_list_services_with_existing_configs(async_client, mock_session):
    """Configured services show is_configured=True with masked key."""
    radarr_cfg = _make_config(ServiceType.RADARR, "http://radarr:7878", "encrypted")

    with (
        patch(
            "app.api.settings.config_repo.get_all_configs",
            new_callable=AsyncMock,
            return_value=[radarr_cfg],
        ),
        patch("app.api.settings.decrypt_api_key", return_value="abcdef1234"),
    ):
        response = await async_client.get("/api/v1/settings/services")

    assert response.status_code == 200
    data = response.json()
    services = {s["service_type"]: s for s in data["services"]}

    assert services["radarr"]["is_configured"] is True
    assert services["radarr"]["url"] == "http://radarr:7878"
    assert services["radarr"]["masked_api_key"] == "******1234"

    assert services["sonarr"]["is_configured"] is False
    assert services["jellyfin"]["is_configured"] is False


@pytest.mark.asyncio
async def test_list_services_all_configured(async_client, mock_session):
    """All 3 services configured → all show is_configured=True."""
    configs = [
        _make_config(ServiceType.RADARR, "http://radarr", "encR"),
        _make_config(ServiceType.SONARR, "http://sonarr", "encS"),
        _make_config(ServiceType.JELLYFIN, "http://jf", "encJ"),
    ]

    with (
        patch(
            "app.api.settings.config_repo.get_all_configs",
            new_callable=AsyncMock,
            return_value=configs,
        ),
        patch("app.api.settings.decrypt_api_key", return_value="key1234567"),
    ):
        response = await async_client.get("/api/v1/settings/services")

    assert response.status_code == 200
    services = response.json()["services"]
    assert all(s["is_configured"] is True for s in services)
    assert len(services) == 3


# ---------------------------------------------------------------------------
# PUT /api/v1/settings/services/{service}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_put_service_new_missing_url_returns_422(async_client, mock_session):
    """Creating a new config without url → 422."""
    with patch(
        "app.api.settings.config_repo.get_config_by_service",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = await async_client.put(
            "/api/v1/settings/services/radarr",
            json={"api_key": "my-key"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_put_service_new_missing_api_key_returns_422(async_client, mock_session):
    """Creating a new config without api_key → 422."""
    with patch(
        "app.api.settings.config_repo.get_config_by_service",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = await async_client.put(
            "/api/v1/settings/services/radarr",
            json={"url": "http://radarr:7878"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_put_service_new_both_fields_returns_200(async_client, mock_session):
    """Creating a new config with both fields → 200, is_configured=True."""
    new_cfg = _make_config(ServiceType.RADARR, "http://radarr:7878", "enc")

    with (
        patch(
            "app.api.settings.config_repo.get_config_by_service",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.api.settings.config_repo.upsert_config",
            new_callable=AsyncMock,
            return_value=new_cfg,
        ),
        patch("app.api.settings.decrypt_api_key", return_value="abcdef1234"),
    ):
        mock_session.commit = AsyncMock()
        response = await async_client.put(
            "/api/v1/settings/services/radarr",
            json={"url": "http://radarr:7878", "api_key": "my-api-key"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["is_configured"] is True
    assert data["service_type"] == "radarr"


@pytest.mark.asyncio
async def test_put_service_partial_update_url_only(async_client, mock_session):
    """Partial update with only url — api_key is preserved from existing config."""
    existing = _make_config(ServiceType.SONARR, "http://old-sonarr", "enc-old")
    updated = _make_config(ServiceType.SONARR, "http://new-sonarr", "enc-old")

    with (
        patch(
            "app.api.settings.config_repo.get_config_by_service",
            new_callable=AsyncMock,
            return_value=existing,
        ),
        patch("app.api.settings.decrypt_api_key", return_value="plain-old-key"),
        patch(
            "app.api.settings.config_repo.upsert_config",
            new_callable=AsyncMock,
            return_value=updated,
        ) as mock_upsert,
    ):
        mock_session.commit = AsyncMock()
        response = await async_client.put(
            "/api/v1/settings/services/sonarr",
            json={"url": "http://new-sonarr"},
        )

    assert response.status_code == 200
    # upsert_config was called with the preserved (decrypted) api_key
    _, _, called_url, called_key = mock_upsert.call_args.args
    assert called_url == "http://new-sonarr"
    assert called_key == "plain-old-key"


@pytest.mark.asyncio
async def test_put_service_invalid_service_type_returns_422(async_client):
    """Unknown service type in path → 422."""
    response = await async_client.put(
        "/api/v1/settings/services/unknown_service",
        json={"url": "http://example.com", "api_key": "key"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/v1/settings/services/{service}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_service_not_found_returns_404(async_client, mock_session):
    """Deleting a non-existent config → 404."""
    mock_session.commit = AsyncMock()
    with patch(
        "app.api.settings.config_repo.delete_config",
        new_callable=AsyncMock,
        return_value=False,
    ):
        response = await async_client.delete("/api/v1/settings/services/radarr")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_service_existing_returns_204(async_client, mock_session):
    """Deleting an existing config → 204."""
    mock_session.commit = AsyncMock()
    with patch(
        "app.api.settings.config_repo.delete_config",
        new_callable=AsyncMock,
        return_value=True,
    ):
        response = await async_client.delete("/api/v1/settings/services/radarr")

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_service_invalid_service_type(async_client):
    """Unknown service type → 422."""
    response = await async_client.delete("/api/v1/settings/services/nonexistent")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/settings/services/{service}/test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_test_service_success(async_client):
    """Successful connection test → 200, success=True."""
    with patch(
        "app.api.settings.test_service_connection",
        new_callable=AsyncMock,
        return_value=(True, "Radarr connection successful"),
    ):
        response = await async_client.post(
            "/api/v1/settings/services/radarr/test",
            json={"url": "http://radarr:7878", "api_key": "my-key"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Radarr" in data["message"]
    assert data["service_type"] == "radarr"


@pytest.mark.asyncio
async def test_test_service_connection_error(async_client):
    """Connection failure → 200 with success=False and error message."""
    with patch(
        "app.api.settings.test_service_connection",
        new_callable=AsyncMock,
        return_value=(False, "Cannot connect to Sonarr: connection refused"),
    ):
        response = await async_client.post(
            "/api/v1/settings/services/sonarr/test",
            json={"url": "http://sonarr:8989", "api_key": "bad-key"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "Cannot connect" in data["message"]


@pytest.mark.asyncio
async def test_test_service_http_error(async_client):
    """HTTP 401 from external service → success=False, status code in message."""
    with patch(
        "app.api.settings.test_service_connection",
        new_callable=AsyncMock,
        return_value=(False, "Jellyfin returned status 401"),
    ):
        response = await async_client.post(
            "/api/v1/settings/services/jellyfin/test",
            json={"url": "http://jellyfin:8096", "api_key": "wrong-key"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "401" in data["message"]


@pytest.mark.asyncio
async def test_test_service_missing_url_returns_422(async_client):
    """Missing url field in test request → 422."""
    response = await async_client.post(
        "/api/v1/settings/services/radarr/test",
        json={"api_key": "my-key"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_test_service_missing_api_key_returns_422(async_client):
    """Missing api_key field in test request → 422."""
    response = await async_client.post(
        "/api/v1/settings/services/radarr/test",
        json={"url": "http://radarr:7878"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_test_service_empty_url_returns_422(async_client):
    """Empty string url violates min_length=1 → 422."""
    response = await async_client.post(
        "/api/v1/settings/services/radarr/test",
        json={"url": "", "api_key": "key"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_test_service_passes_correct_args_to_connection_test(async_client):
    """Correct url/api_key are forwarded to test_service_connection."""
    with patch(
        "app.api.settings.test_service_connection",
        new_callable=AsyncMock,
        return_value=(True, "ok"),
    ) as mock_test:
        await async_client.post(
            "/api/v1/settings/services/jellyfin/test",
            json={"url": "http://myjellyfin.local", "api_key": "token-xyz"},
        )

    mock_test.assert_awaited_once_with(ServiceType.JELLYFIN, "http://myjellyfin.local", "token-xyz")
