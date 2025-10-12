# tests/units/test_radarr_import.py
from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import AsyncClient

from app.database import get_session
from app.main import app


@pytest.mark.asyncio
async def test_import_radarr_success():
    # Mock the session
    mock_session = AsyncMock()

    # Mock fetch_radarr_movies to return sample movies
    sample_movies = [
        {"id": 1, "title": "Movie 1", "inCinemas": "2023-01-01T00:00:00Z"},
        {"id": 2, "title": "Movie 2", "inCinemas": "2023-02-01T00:00:00Z"},
    ]

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = sample_movies

        # Mock session.execute for exists check (assume no existing movies)
        mock_result = Mock()
        mock_result.scalar.return_value = False
        mock_session.execute.return_value = mock_result

        mock_session.add = Mock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        # Override the session dependency
        async def override_get_session():
            return mock_session

        app.dependency_overrides[get_session] = override_get_session

        # Call the endpoint using AsyncClient
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/api/v1/radarr/import")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "imported": 2}

        # Verify mocks
        mock_fetch.assert_called_once()
        assert mock_session.execute.call_count == 2
        assert mock_session.add.call_count == 4  # Two Media and two Movie objects
        assert mock_session.flush.call_count == 2
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

    # Clean up overrides
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_import_radarr_partial_insert_failure():
    # Mock the session
    mock_session = AsyncMock()

    # Mock fetch_radarr_movies to return sample movies
    sample_movies = [
        {"id": 1, "title": "Movie 1", "inCinemas": "2023-01-01T00:00:00Z"},
        {"id": 2, "title": "Movie 2", "inCinemas": "2023-02-01T00:00:00Z"},
    ]

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = sample_movies

        # Mock session.execute for exists check (assume no existing movies)
        mock_result = Mock()
        mock_result.scalar.return_value = False
        mock_session.execute.return_value = mock_result

        # Mock session.add, commit, rollback
        mock_session.add = Mock()  # Обычный Mock вместо AsyncMock
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        # Mock flush to succeed for first, fail for second
        mock_session.flush.side_effect = [None, Exception("Flush failed")]

        # Override the session dependency
        async def override_get_session():
            return mock_session

        app.dependency_overrides[get_session] = override_get_session

        # Call the endpoint
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/api/v1/radarr/import")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "imported": 1}

        # Verify mocks
        mock_fetch.assert_called_once()
        assert mock_session.execute.call_count == 2
        assert mock_session.add.call_count == 3
        assert mock_session.flush.call_count == 2
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_called_once()

    # Clean up overrides
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_import_radarr_commit_failure():
    # Mock the session
    mock_session = AsyncMock()

    # Mock fetch_radarr_movies to return sample movies
    sample_movies = [{"id": 1, "title": "Movie 1", "inCinemas": "2023-01-01T00:00:00Z"}]

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = sample_movies

        # Mock session.execute for exists check
        mock_result = Mock()
        mock_result.scalar.return_value = False
        mock_session.execute.return_value = mock_result

        # Mock session.add, flush
        mock_session.add = Mock()  # Обычный Mock вместо AsyncMock
        mock_session.flush = AsyncMock()

        # Mock commit to raise exception
        mock_session.commit.side_effect = Exception("Commit failed")
        mock_session.rollback = AsyncMock()

        # Override the session dependency
        async def override_get_session():
            return mock_session

        app.dependency_overrides[get_session] = override_get_session

        # Call the endpoint
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/api/v1/radarr/import")

        assert response.status_code == 500
        assert "Commit failed" in response.json().get("detail", "")

        # Verify mocks
        mock_fetch.assert_called_once()
        assert mock_session.execute.call_count == 1
        assert mock_session.add.call_count == 2
        assert mock_session.flush.call_count == 1
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_called_once()

    # Clean up overrides
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_import_radarr_existing_movies():
    # Mock the session
    mock_session = AsyncMock()

    # Mock fetch_radarr_movies to return sample movies
    sample_movies = [{"id": 1, "title": "Movie 1", "inCinemas": "2023-01-01T00:00:00Z"}]

    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = sample_movies

        # Mock session.execute for exists check (assume movie exists)
        mock_result = Mock()
        mock_result.scalar.return_value = True
        mock_session.execute.return_value = mock_result

        # Mock session.add, flush, commit, rollback (should not be called for inserts)
        mock_session.add = Mock()  # Обычный Mock вместо AsyncMock
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        # Override the session dependency
        async def override_get_session():
            return mock_session

        app.dependency_overrides[get_session] = override_get_session

        # Call the endpoint
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/api/v1/radarr/import")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "imported": 0}

        # Verify mocks
        mock_fetch.assert_called_once()
        assert mock_session.execute.call_count == 1
        mock_session.add.assert_not_called()
        mock_session.flush.assert_not_called()
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

    # Clean up overrides
    app.dependency_overrides = {}
