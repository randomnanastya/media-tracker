"""Integration tests for /api/v1/settings/services with a real PostgreSQL DB."""

from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from app.models import ServiceConfig, ServiceType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_URL = "http://radarr:7878"
_TEST_KEY = "my-plain-api-key-12345"

# Use a stable Fernet-compatible encryption key for integration tests
_FERNET_KEY = "Yw1UOJf9F_KlNf3Px34rRqhSPmhbqTKXQiANfC-rFzI="


async def _create_config(
    session,
    service_type: ServiceType,
    url: str = _TEST_URL,
    api_key: str = _TEST_KEY,
) -> ServiceConfig:
    """Insert a ServiceConfig directly into the DB."""
    from app.services import service_config_repository as repo

    cfg = await repo.upsert_config(session, service_type, url, api_key)
    await session.commit()
    return cfg


# ---------------------------------------------------------------------------
# GET — returns all 3 services
# ---------------------------------------------------------------------------


async def test_list_services_empty_db(client_with_db, monkeypatch):
    """Without any DB configs all 3 services have is_configured=False."""
    monkeypatch.setenv("ENCRYPTION_KEY", _FERNET_KEY)

    import app.utils.encryption as enc_module

    monkeypatch.setattr(enc_module, "_fernet", None)

    response = await client_with_db.get("/api/v1/settings/services")

    assert response.status_code == 200
    data = response.json()
    services = data["services"]
    assert len(services) == 3
    for svc in services:
        assert svc["is_configured"] is False


async def test_list_services_after_create(client_with_db, session_for_test, monkeypatch):
    """After creating one config, only that service shows is_configured=True."""
    monkeypatch.setenv("ENCRYPTION_KEY", _FERNET_KEY)

    import app.utils.encryption as enc_module

    monkeypatch.setattr(enc_module, "_fernet", None)

    await _create_config(session_for_test, ServiceType.RADARR)

    response = await client_with_db.get("/api/v1/settings/services")
    assert response.status_code == 200

    services = {s["service_type"]: s for s in response.json()["services"]}
    assert services["radarr"]["is_configured"] is True
    assert services["sonarr"]["is_configured"] is False
    assert services["jellyfin"]["is_configured"] is False


# ---------------------------------------------------------------------------
# PUT — create / update
# ---------------------------------------------------------------------------


async def test_put_creates_new_config(client_with_db, session_for_test, monkeypatch):
    """PUT with url + api_key creates a new ServiceConfig row."""
    monkeypatch.setenv("ENCRYPTION_KEY", _FERNET_KEY)

    import app.utils.encryption as enc_module

    monkeypatch.setattr(enc_module, "_fernet", None)

    response = await client_with_db.put(
        "/api/v1/settings/services/sonarr",
        json={"url": "http://sonarr:8989", "api_key": "sonarr-key-abc"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["service_type"] == "sonarr"
    assert data["is_configured"] is True
    assert data["url"] == "http://sonarr:8989"
    # Key should be masked, not plain
    assert "sonarr-key-abc" not in data["masked_api_key"]

    # Verify DB state
    result = await session_for_test.execute(
        select(ServiceConfig).where(ServiceConfig.service_type == ServiceType.SONARR)
    )
    cfg = result.scalar_one_or_none()
    assert cfg is not None
    assert cfg.url == "http://sonarr:8989"


async def test_put_updates_existing_config(client_with_db, session_for_test, monkeypatch):
    """Second PUT on same service updates existing record (no duplicate)."""
    monkeypatch.setenv("ENCRYPTION_KEY", _FERNET_KEY)

    import app.utils.encryption as enc_module

    monkeypatch.setattr(enc_module, "_fernet", None)

    # Create initial
    await _create_config(session_for_test, ServiceType.RADARR, url="http://old:7878")

    # Update
    response = await client_with_db.put(
        "/api/v1/settings/services/radarr",
        json={"url": "http://new:7878", "api_key": "updated-key"},
    )

    assert response.status_code == 200
    assert response.json()["url"] == "http://new:7878"

    # Only one row should exist
    result = await session_for_test.execute(select(ServiceConfig))
    all_configs = result.scalars().all()
    assert len(all_configs) == 1
    assert all_configs[0].url == "http://new:7878"


async def test_put_partial_update_url_preserves_key(client_with_db, session_for_test, monkeypatch):
    """PUT with only url keeps the previously stored api_key."""
    monkeypatch.setenv("ENCRYPTION_KEY", _FERNET_KEY)

    import app.utils.encryption as enc_module

    monkeypatch.setattr(enc_module, "_fernet", None)

    original_key = "original-api-key-9999"
    await _create_config(
        session_for_test, ServiceType.JELLYFIN, url="http://jf:8096", api_key=original_key
    )

    # Save config before update (for expire after partial update)
    result = await session_for_test.execute(
        select(ServiceConfig).where(ServiceConfig.service_type == ServiceType.JELLYFIN)
    )
    before_cfg = result.scalar_one()

    # Partial update: url only
    response = await client_with_db.put(
        "/api/v1/settings/services/jellyfin",
        json={"url": "http://jf-new:8096"},
    )

    assert response.status_code == 200

    # Refresh
    session_for_test.expire(before_cfg)
    result2 = await session_for_test.execute(
        select(ServiceConfig).where(ServiceConfig.service_type == ServiceType.JELLYFIN)
    )
    after_cfg = result2.scalar_one()
    assert after_cfg.url == "http://jf-new:8096"

    # The encrypted key should encode the same plain value
    from app.utils.encryption import decrypt_api_key

    assert decrypt_api_key(after_cfg.encrypted_api_key) == original_key


async def test_put_new_config_without_url_returns_422(client_with_db, monkeypatch):
    """Creating a new config with missing url → 422 (no existing row)."""
    monkeypatch.setenv("ENCRYPTION_KEY", _FERNET_KEY)

    import app.utils.encryption as enc_module

    monkeypatch.setattr(enc_module, "_fernet", None)

    response = await client_with_db.put(
        "/api/v1/settings/services/radarr",
        json={"api_key": "only-key"},
    )
    assert response.status_code == 422


async def test_put_strips_trailing_slash_from_url(client_with_db, session_for_test, monkeypatch):
    """Trailing slash is stripped from URL before storage."""
    monkeypatch.setenv("ENCRYPTION_KEY", _FERNET_KEY)

    import app.utils.encryption as enc_module

    monkeypatch.setattr(enc_module, "_fernet", None)

    await client_with_db.put(
        "/api/v1/settings/services/radarr",
        json={"url": "http://radarr:7878/", "api_key": "key"},
    )

    result = await session_for_test.execute(
        select(ServiceConfig).where(ServiceConfig.service_type == ServiceType.RADARR)
    )
    cfg = result.scalar_one_or_none()
    assert cfg is not None
    assert not cfg.url.endswith("/")


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------


async def test_delete_existing_config_returns_204(client_with_db, session_for_test, monkeypatch):
    """DELETE existing config → 204 and row removed from DB."""
    monkeypatch.setenv("ENCRYPTION_KEY", _FERNET_KEY)

    import app.utils.encryption as enc_module

    monkeypatch.setattr(enc_module, "_fernet", None)

    await _create_config(session_for_test, ServiceType.RADARR)

    response = await client_with_db.delete("/api/v1/settings/services/radarr")

    assert response.status_code == 204

    result = await session_for_test.execute(
        select(ServiceConfig).where(ServiceConfig.service_type == ServiceType.RADARR)
    )
    assert result.scalar_one_or_none() is None


async def test_delete_nonexistent_config_returns_404(client_with_db, monkeypatch):
    """DELETE on a service that has no config → 404."""
    monkeypatch.setenv("ENCRYPTION_KEY", _FERNET_KEY)

    import app.utils.encryption as enc_module

    monkeypatch.setattr(enc_module, "_fernet", None)

    response = await client_with_db.delete("/api/v1/settings/services/sonarr")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Full CRUD cycle
# ---------------------------------------------------------------------------


async def test_full_crud_cycle(client_with_db, session_for_test, monkeypatch):
    """Create → Read → Update → Delete — full lifecycle."""
    monkeypatch.setenv("ENCRYPTION_KEY", _FERNET_KEY)

    import app.utils.encryption as enc_module

    monkeypatch.setattr(enc_module, "_fernet", None)

    # Create
    create_resp = await client_with_db.put(
        "/api/v1/settings/services/radarr",
        json={"url": "http://radarr:7878", "api_key": "first-key"},
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["is_configured"] is True

    # Read
    list_resp = await client_with_db.get("/api/v1/settings/services")
    services = {s["service_type"]: s for s in list_resp.json()["services"]}
    assert services["radarr"]["is_configured"] is True

    # Update
    update_resp = await client_with_db.put(
        "/api/v1/settings/services/radarr",
        json={"url": "http://radarr-updated:7878", "api_key": "second-key"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["url"] == "http://radarr-updated:7878"

    # Delete
    del_resp = await client_with_db.delete("/api/v1/settings/services/radarr")
    assert del_resp.status_code == 204

    # Verify gone
    list_after = await client_with_db.get("/api/v1/settings/services")
    services_after = {s["service_type"]: s for s in list_after.json()["services"]}
    assert services_after["radarr"]["is_configured"] is False


# ---------------------------------------------------------------------------
# Upsert uniqueness
# ---------------------------------------------------------------------------


async def test_upsert_does_not_create_duplicate_rows(client_with_db, session_for_test, monkeypatch):
    """Multiple PUTs on the same service → only one row in DB."""
    monkeypatch.setenv("ENCRYPTION_KEY", _FERNET_KEY)

    import app.utils.encryption as enc_module

    monkeypatch.setattr(enc_module, "_fernet", None)

    for i in range(3):
        await client_with_db.put(
            "/api/v1/settings/services/sonarr",
            json={"url": f"http://sonarr:{8989 + i}", "api_key": f"key-{i}"},
        )

    result = await session_for_test.execute(
        select(ServiceConfig).where(ServiceConfig.service_type == ServiceType.SONARR)
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].url == "http://sonarr:8991"


# ---------------------------------------------------------------------------
# POST /test — mock httpx
# ---------------------------------------------------------------------------


async def test_test_service_success_integration(client_with_db, monkeypatch):
    """POST /test with mocked httpx returns success=True."""
    monkeypatch.setenv("ENCRYPTION_KEY", _FERNET_KEY)

    with patch(
        "app.services.service_test.httpx.AsyncClient",
    ) as mock_client_cls:
        mock_response = AsyncMock()
        mock_response.raise_for_status = AsyncMock()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_http

        response = await client_with_db.post(
            "/api/v1/settings/services/radarr/test",
            json={"url": "http://radarr:7878", "api_key": "testkey"},
        )

    assert response.status_code == 200
    assert response.json()["success"] is True


async def test_test_service_connection_refused_integration(client_with_db, monkeypatch):
    """POST /test when httpx raises RequestError → success=False."""
    import httpx

    monkeypatch.setenv("ENCRYPTION_KEY", _FERNET_KEY)

    with patch(
        "app.services.service_test.httpx.AsyncClient",
    ) as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(side_effect=httpx.RequestError("Connection refused"))
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_http

        response = await client_with_db.post(
            "/api/v1/settings/services/sonarr/test",
            json={"url": "http://sonarr:8989", "api_key": "testkey"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "Cannot connect" in data["message"]
