from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from app.models import RefreshToken
from app.services import auth_service
from app.utils.security import (
    generate_recovery_code,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from tests.factories import AppUserFactory, RefreshTokenFactory


@pytest.mark.asyncio
async def test_is_setup_required_true(mock_session: AsyncMock) -> None:
    mock_result = Mock()
    mock_result.scalar_one.return_value = 0
    mock_session.execute.return_value = mock_result

    result = await auth_service.is_setup_required(mock_session)

    assert result is True


@pytest.mark.asyncio
async def test_is_setup_required_false(mock_session: AsyncMock) -> None:
    mock_result = Mock()
    mock_result.scalar_one.return_value = 1
    mock_session.execute.return_value = mock_result

    result = await auth_service.is_setup_required(mock_session)

    assert result is False


@pytest.mark.asyncio
async def test_register_user_success(mock_session: AsyncMock) -> None:
    count_result = Mock()
    count_result.scalar_one.return_value = 0
    existing_result = Mock()
    existing_result.scalar_one_or_none.return_value = None
    mock_session.execute.side_effect = [count_result, existing_result]

    user, recovery_code = await auth_service.register_user(mock_session, "newuser", "password123")

    assert user is not None
    assert isinstance(recovery_code, str)
    parts = recovery_code.split("-")
    assert len(parts) == 4
    assert all(len(p) == 5 for p in parts)
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_register_user_registration_closed(mock_session: AsyncMock) -> None:
    count_result = Mock()
    count_result.scalar_one.return_value = 1
    mock_session.execute.return_value = count_result

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.register_user(mock_session, "user", "pass12345")

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_register_user_username_taken(mock_session: AsyncMock) -> None:
    count_result = Mock()
    count_result.scalar_one.return_value = 0
    existing_result = Mock()
    existing_result.scalar_one_or_none.return_value = AppUserFactory.build()
    mock_session.execute.side_effect = [count_result, existing_result]

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.register_user(mock_session, "taken", "pass12345")

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_authenticate_user_success(mock_session: AsyncMock) -> None:
    user = AppUserFactory.build(hashed_password=hash_password("correctpass"))
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = user
    mock_session.execute.return_value = mock_result

    result = await auth_service.authenticate_user(mock_session, user.username, "correctpass")

    assert result is user
    assert result.last_login_at is not None


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(mock_session: AsyncMock) -> None:
    user = AppUserFactory.build(hashed_password=hash_password("correctpass"))
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = user
    mock_session.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.authenticate_user(mock_session, user.username, "wrongpass")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_authenticate_user_not_found(mock_session: AsyncMock) -> None:
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.authenticate_user(mock_session, "nouser", "anypass")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_create_refresh_token(mock_session: AsyncMock) -> None:
    raw_token = await auth_service.create_refresh_token(mock_session, user_id=1)

    assert isinstance(raw_token, str)
    assert len(raw_token) > 10
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()

    added_obj = mock_session.add.call_args[0][0]
    assert isinstance(added_obj, RefreshToken)
    assert added_obj.user_id == 1
    assert not added_obj.revoked


@pytest.mark.asyncio
async def test_revoke_refresh_token(mock_session: AsyncMock) -> None:
    raw = generate_refresh_token()
    token = RefreshTokenFactory.build(token_hash=hash_token(raw), revoked=False)
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = token
    mock_session.execute.return_value = mock_result

    await auth_service.revoke_refresh_token(mock_session, raw)

    assert token.revoked is True


@pytest.mark.asyncio
async def test_reset_password_with_code_success(mock_session: AsyncMock) -> None:
    raw_code = generate_recovery_code()
    user = AppUserFactory.build(recovery_code_hash=hash_token(raw_code))
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = user
    mock_session.execute.return_value = mock_result

    returned_user, new_code = await auth_service.reset_password_with_code(
        mock_session, raw_code, "newpass123"
    )

    assert returned_user is user
    assert "-" in new_code


@pytest.mark.asyncio
async def test_reset_password_with_code_invalid(mock_session: AsyncMock) -> None:
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.reset_password_with_code(mock_session, "WRONG-CODE-XXXX-YYYY", "newpass")

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_change_password_success(mock_session: AsyncMock) -> None:
    user = AppUserFactory.build(hashed_password=hash_password("oldpass"))
    mock_session.execute.return_value = Mock()

    await auth_service.change_password(mock_session, user, "oldpass", "newpass123")

    assert verify_password("newpass123", user.hashed_password)


@pytest.mark.asyncio
async def test_change_password_wrong_current(mock_session: AsyncMock) -> None:
    user = AppUserFactory.build(hashed_password=hash_password("correctpass"))

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.change_password(mock_session, user, "wrongpass", "newpass123")

    assert exc_info.value.status_code == 400


# === refresh_access_token ===


@pytest.mark.asyncio
async def test_refresh_access_token_success(mock_session: AsyncMock) -> None:
    from datetime import UTC, datetime, timedelta

    raw = generate_refresh_token()
    future = datetime.now(UTC) + timedelta(days=30)
    token = RefreshTokenFactory.build(token_hash=hash_token(raw), revoked=False, expires_at=future)

    lookup_result = Mock()
    lookup_result.scalar_one_or_none.return_value = token
    mock_session.execute.return_value = lookup_result

    result = await auth_service.refresh_access_token(mock_session, raw, "test-secret", 15)

    assert isinstance(result, tuple)
    assert len(result) == 2
    new_access, new_refresh = result
    assert isinstance(new_access, str)
    assert isinstance(new_refresh, str)
    assert token.revoked is True


@pytest.mark.asyncio
async def test_refresh_access_token_revoked(mock_session: AsyncMock) -> None:
    raw = generate_refresh_token()
    token = RefreshTokenFactory.build(token_hash=hash_token(raw), revoked=True)

    lookup_result = Mock()
    lookup_result.scalar_one_or_none.return_value = token
    mock_session.execute.return_value = lookup_result

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.refresh_access_token(mock_session, raw, "test-secret", 15)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_refresh_access_token_expired(mock_session: AsyncMock) -> None:
    from datetime import UTC, datetime, timedelta

    raw = generate_refresh_token()
    past = datetime.now(UTC) - timedelta(days=1)
    token = RefreshTokenFactory.build(token_hash=hash_token(raw), revoked=False, expires_at=past)

    lookup_result = Mock()
    lookup_result.scalar_one_or_none.return_value = token
    mock_session.execute.return_value = lookup_result

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.refresh_access_token(mock_session, raw, "test-secret", 15)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_refresh_access_token_not_found(mock_session: AsyncMock) -> None:
    lookup_result = Mock()
    lookup_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = lookup_result

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.refresh_access_token(
            mock_session, "nonexistent-token", "test-secret", 15
        )

    assert exc_info.value.status_code == 401


# === update_user_profile ===


@pytest.mark.asyncio
async def test_update_user_profile_success(mock_session: AsyncMock) -> None:
    user = AppUserFactory.build(username="oldname", email="old@test.com")
    conflict_result = Mock()
    conflict_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = conflict_result

    returned = await auth_service.update_user_profile(
        mock_session, user, username="newname", email="new@test.com"
    )

    assert returned.username == "newname"
    assert returned.email == "new@test.com"
    assert returned is user


@pytest.mark.asyncio
async def test_update_user_profile_username_taken(mock_session: AsyncMock) -> None:
    user = AppUserFactory.build(username="myname")
    other_user = AppUserFactory.build(username="takenname")
    conflict_result = Mock()
    conflict_result.scalar_one_or_none.return_value = other_user
    mock_session.execute.return_value = conflict_result

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.update_user_profile(mock_session, user, username="takenname")

    assert exc_info.value.status_code == 409


# === regenerate_recovery_code ===


@pytest.mark.asyncio
async def test_regenerate_recovery_code(mock_session: AsyncMock) -> None:
    user = AppUserFactory.build(recovery_code_hash=None)

    raw_code = await auth_service.regenerate_recovery_code(mock_session, user)

    assert isinstance(raw_code, str)
    parts = raw_code.split("-")
    assert len(parts) == 4
    assert all(len(p) == 5 for p in parts)
    assert user.recovery_code_hash is not None
    assert user.recovery_code_hash != raw_code
