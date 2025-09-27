import json

import pytest
import asyncio
import os
from unittest.mock import patch, AsyncMock, MagicMock

from _pytest import pathlib

# set tests env database
os.environ.update({
    'POSTGRES_HOST': 'localhost',
    'POSTGRES_PORT': '5432',
    'POSTGRES_USER': 'test',
    'POSTGRES_PASSWORD': 'test',
    'POSTGRES_DB': 'test',
    'APP_ENV': 'testing'
})

# mock scheduler before imports
with patch('apscheduler.schedulers.asyncio.AsyncIOScheduler') as mock_scheduler:
    mock_scheduler_instance = MagicMock()
    mock_scheduler_instance.start = MagicMock()
    mock_scheduler.return_value = mock_scheduler_instance

    # imports fixtures
    from tests.units.fixtures.radarr_movies import (
        RADARR_MOVIES_BASIC,
        RADARR_MOVIES_EMPTY,
        RADARR_MOVIES_WITH_INVALID_DATA,
        RADARR_MOVIES_LARGE_LIST,
        RADARR_MOVIES_WITH_SPECIAL_CHARACTERS,
    )


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_app():
    with patch('sqlalchemy.ext.asyncio.create_async_engine') as mock_engine, \
            patch('apscheduler.schedulers.asyncio.AsyncIOScheduler') as mock_sch:
        mock_engine.return_value = AsyncMock()
        mock_scheduler_inst = MagicMock()
        mock_scheduler_inst.start = MagicMock()
        mock_sch.return_value = mock_scheduler_inst

        from app.main import app
        from fastapi.testclient import TestClient

        return TestClient(app)

@pytest.fixture
def radarr_movies_basic():
    return RADARR_MOVIES_BASIC.copy()


@pytest.fixture
def radarr_movies_empty():
    return RADARR_MOVIES_EMPTY.copy()


@pytest.fixture
def radarr_movies_invalid_data():
    return RADARR_MOVIES_WITH_INVALID_DATA.copy()


@pytest.fixture
def radarr_movies_large_list():
    return RADARR_MOVIES_LARGE_LIST.copy()


@pytest.fixture
def radarr_movies_special_chars():
    return RADARR_MOVIES_WITH_SPECIAL_CHARACTERS.copy()


@pytest.fixture
def mock_radarr_movie_single():
    return {
        "id": 1,
        "title": "Single Test Movie",
        "inCinemas": "2023-01-01T00:00:00Z",
        "year": 2023,
        "tmdbId": 12345
    }

@pytest.fixture
def radarr_movies_from_json():
    path = pathlib.Path(__file__).parent / "fixtures" / "data" / "movies.json"
    if not path.exists():
        raise FileNotFoundError(f"movies.json not found at: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def mock_database_session():
    with patch('app.services.radarr_service.AsyncSessionLocal') as mock_session:
        mock_async_session = AsyncMock()

        mock_async_session.add = MagicMock()
        mock_async_session.flush = AsyncMock()
        mock_async_session.commit = AsyncMock()
        mock_async_session.rollback = AsyncMock()

        mock_result = AsyncMock()

        mock_result.scalar = MagicMock(return_value=False)
        mock_async_session.execute.return_value = mock_result

        mock_session.return_value.__aenter__.return_value = mock_async_session

        yield mock_async_session