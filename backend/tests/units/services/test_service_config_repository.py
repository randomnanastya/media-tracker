"""Unit tests for app.services.service_config_repository (no real DB)."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

from app.models import ServiceConfig, ServiceType
from app.services import service_config_repository as repo

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session(scalars_result=None, scalar_one_or_none=None, rowcount=0):
    """Build a minimal AsyncMock that mimics AsyncSession behaviour."""
    session = AsyncMock()
    session.add = Mock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    execute_result = MagicMock()

    # scalars().all() path used by get_all_configs
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = scalars_result if scalars_result is not None else []
    execute_result.scalars.return_value = scalars_mock

    # scalar_one_or_none() path used by get_config_by_service
    execute_result.scalar_one_or_none.return_value = scalar_one_or_none

    # rowcount used by delete_config
    execute_result.rowcount = rowcount

    session.execute = AsyncMock(return_value=execute_result)
    return session


def _make_config(service_type: ServiceType, url: str, encrypted_key: str) -> ServiceConfig:
    cfg = MagicMock(spec=ServiceConfig)
    cfg.id = 1
    cfg.service_type = service_type
    cfg.url = url
    cfg.encrypted_api_key = encrypted_key
    return cfg


# ---------------------------------------------------------------------------
# get_all_configs
# ---------------------------------------------------------------------------


async def test_get_all_configs_empty():
    session = _make_session(scalars_result=[])
    result = await repo.get_all_configs(session)
    assert result == []
    session.execute.assert_awaited_once()


async def test_get_all_configs_returns_configs():
    cfg1 = _make_config(ServiceType.RADARR, "http://radarr", "enc1")
    cfg2 = _make_config(ServiceType.SONARR, "http://sonarr", "enc2")
    session = _make_session(scalars_result=[cfg1, cfg2])

    result = await repo.get_all_configs(session)
    assert len(result) == 2
    assert result[0].service_type == ServiceType.RADARR
    assert result[1].service_type == ServiceType.SONARR


# ---------------------------------------------------------------------------
# get_config_by_service
# ---------------------------------------------------------------------------


async def test_get_config_by_service_not_found():
    session = _make_session(scalar_one_or_none=None)
    result = await repo.get_config_by_service(session, ServiceType.RADARR)
    assert result is None


async def test_get_config_by_service_found():
    cfg = _make_config(ServiceType.JELLYFIN, "http://jf", "enc")
    session = _make_session(scalar_one_or_none=cfg)
    result = await repo.get_config_by_service(session, ServiceType.JELLYFIN)
    assert result is cfg


# ---------------------------------------------------------------------------
# upsert_config — create new
# ---------------------------------------------------------------------------


async def test_upsert_config_creates_new_calls_session_add():
    """When no existing config, session.add must be called once."""
    session = _make_session(scalar_one_or_none=None)

    with patch("app.services.service_config_repository.encrypt_api_key", return_value="encrypted"):
        result = await repo.upsert_config(session, ServiceType.RADARR, "http://radarr/", "key123")

    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    assert isinstance(result, ServiceConfig)
    assert result.service_type == ServiceType.RADARR


async def test_upsert_config_create_strips_trailing_slash():
    """URL trailing slash is stripped during create."""
    session = _make_session(scalar_one_or_none=None)

    with patch("app.services.service_config_repository.encrypt_api_key", return_value="enc"):
        result = await repo.upsert_config(session, ServiceType.RADARR, "http://radarr/", "key")

    assert result.url == "http://radarr"


# ---------------------------------------------------------------------------
# upsert_config — update existing
# ---------------------------------------------------------------------------


async def test_upsert_config_updates_existing_no_session_add():
    """When config already exists, session.add must NOT be called."""
    existing = _make_config(ServiceType.SONARR, "http://old", "old_enc")
    session = _make_session(scalar_one_or_none=existing)

    with patch("app.services.service_config_repository.encrypt_api_key", return_value="new_enc"):
        result = await repo.upsert_config(
            session, ServiceType.SONARR, "http://sonarr/new/", "newkey"
        )

    session.add.assert_not_called()
    session.flush.assert_awaited_once()
    # Existing object mutated in-place
    assert result is existing
    assert result.url == "http://sonarr/new"
    assert result.encrypted_api_key == "new_enc"


async def test_upsert_config_update_strips_trailing_slash():
    """URL trailing slash stripped on update too."""
    existing = _make_config(ServiceType.JELLYFIN, "http://old", "enc")
    session = _make_session(scalar_one_or_none=existing)

    with patch("app.services.service_config_repository.encrypt_api_key", return_value="e"):
        result = await repo.upsert_config(
            session, ServiceType.JELLYFIN, "http://jellyfin:8096/", "k"
        )

    assert result.url == "http://jellyfin:8096"


# ---------------------------------------------------------------------------
# delete_config
# ---------------------------------------------------------------------------


async def test_delete_config_returns_true_when_deleted():
    session = _make_session(rowcount=1)
    deleted = await repo.delete_config(session, ServiceType.RADARR)
    assert deleted is True
    session.flush.assert_awaited_once()


async def test_delete_config_returns_false_when_not_found():
    session = _make_session(rowcount=0)
    deleted = await repo.delete_config(session, ServiceType.SONARR)
    assert deleted is False


# ---------------------------------------------------------------------------
# get_decrypted_config
# ---------------------------------------------------------------------------


async def test_get_decrypted_config_returns_none_when_not_configured():
    session = _make_session(scalar_one_or_none=None)
    result = await repo.get_decrypted_config(session, ServiceType.RADARR)
    assert result is None


async def test_get_decrypted_config_returns_url_and_decrypted_key():
    cfg = _make_config(ServiceType.RADARR, "http://radarr", "encrypted-token")
    session = _make_session(scalar_one_or_none=cfg)

    with patch("app.services.service_config_repository.decrypt_api_key", return_value="plain-key"):
        result = await repo.get_decrypted_config(session, ServiceType.RADARR)

    assert result is not None
    url, key = result
    assert url == "http://radarr"
    assert key == "plain-key"


async def test_get_decrypted_config_passes_correct_encrypted_key_to_decrypt():
    """decrypt_api_key receives the stored encrypted_api_key value."""
    cfg = _make_config(ServiceType.SONARR, "http://sonarr", "my-encrypted-blob")
    session = _make_session(scalar_one_or_none=cfg)

    with patch(
        "app.services.service_config_repository.decrypt_api_key", return_value="decoded"
    ) as mock_decrypt:
        await repo.get_decrypted_config(session, ServiceType.SONARR)

    mock_decrypt.assert_called_once_with("my-encrypted-blob")
