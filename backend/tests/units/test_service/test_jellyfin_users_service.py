from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.jellyfin_users_service import import_jellyfin_users


@pytest.fixture
def jellyfin_users_basic():
    return [
        {"Id": "user1", "Name": "Alice"},
        {"Id": "user2", "Name": "Bob"},
    ]


@pytest.fixture
def jellyfin_users_update():
    return [
        {"Id": "user1", "Name": "Alice Updated"},
    ]


@pytest.mark.asyncio
async def test_import_jellyfin_users_creates_new_users(
    mock_session, jellyfin_users_basic, mock_scalar_result
):
    # Mock the fetch_jellyfin_users function
    with patch(
        "app.services.jellyfin_users_service.fetch_jellyfin_users", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = jellyfin_users_basic

        # Configure mock_session.execute to return the mock_scalar_result directly
        mock_session.execute.return_value = mock_scalar_result(None)

        # Act
        result = await import_jellyfin_users(mock_session)

        # Assert
        assert result.imported_count == 2
        assert mock_session.add.call_count == 2
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_import_jellyfin_users_updates_existing_user(mock_session, jellyfin_users_update):
    """Should update username if changed"""
    # Existing user
    existing_user = Mock()
    existing_user.username = "Alice"
    existing_user.jellyfin_user_id = "user1"

    mock_result = Mock()
    mock_scalar = Mock()
    mock_scalar.first.return_value = existing_user
    mock_result.scalars.return_value = mock_scalar

    mock_session.execute.return_value = mock_result

    # Mock the fetch_jellyfin_users function
    with patch(
        "app.services.jellyfin_users_service.fetch_jellyfin_users", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = jellyfin_users_update

        result = await import_jellyfin_users(mock_session)

        assert result.imported_count == 0
        assert result.updated_count == 1
        assert existing_user.username == "Alice Updated"
        mock_session.add.assert_called_once_with(existing_user)
        mock_session.flush.assert_called_once()
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_import_jellyfin_users_skips_no_id(mock_session):
    """Should skip users without Id"""
    users = [{"Name": "No ID"}]

    with patch(
        "app.services.jellyfin_users_service.fetch_jellyfin_users", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = users

        result = await import_jellyfin_users(mock_session)

        assert result.imported_count == 0
        assert result.updated_count == 0
        mock_session.add.assert_not_called()
        mock_session.commit.assert_called_once()
