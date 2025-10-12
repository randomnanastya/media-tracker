import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from _pytest import pathlib
from httpx import AsyncClient

# Устанавливаем тестовое окружение
os.environ.update(
    {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "APP_ENV": "testing",
    }
)

# --- Мокаем APScheduler, чтобы app.main импортировался без запуска реального планировщика ---
with patch("apscheduler.schedulers.asyncio.AsyncIOScheduler") as mock_scheduler:
    mock_scheduler_instance = MagicMock()
    mock_scheduler_instance.start = MagicMock()
    mock_scheduler.return_value = mock_scheduler_instance

    # Импорты внутри мока (иначе app.main создаст реальный scheduler)
    from app.main import app
    from tests.units.fixtures.radarr_movies import (
        RADARR_MOVIES_BASIC,
        RADARR_MOVIES_EMPTY,
        RADARR_MOVIES_LARGE_LIST,
        RADARR_MOVIES_WITH_INVALID_DATA,
        RADARR_MOVIES_WITH_SPECIAL_CHARACTERS,
    )


# --- EVENT LOOP (для pytest-asyncio) ---
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# --- Моки базы данных и зависимостей ---
@pytest.fixture
def mock_session():
    """Асинхронный мок SQLAlchemy-сессии"""
    mock = AsyncMock()
    mock.add = Mock()
    mock.flush = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    mock.execute = AsyncMock()
    return mock


@pytest.fixture
def override_session_dependency(mock_session):
    """Переопределение FastAPI зависимости get_session"""

    async def override_get_session():
        yield mock_session

    from app.database import get_session
    from app.main import app

    app.dependency_overrides[get_session] = override_get_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(override_session_dependency):
    """HTTP-клиент для тестирования API"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# --- Моки фильмов из Radarr ---
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


# --- Пример мока из JSON (если понадобится позже) ---
@pytest.fixture
def radarr_movies_from_json():
    path = pathlib.Path(__file__).parent / "fixtures" / "data" / "movies.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_movies_basic():
    """Basic sample movies for testing"""
    return [
        {"id": 1, "title": "Movie 1", "inCinemas": "2023-01-01T00:00:00Z"},
        {"id": 2, "title": "Movie 2", "inCinemas": "2023-02-01T00:00:00Z"},
    ]


@pytest.fixture
def sample_movies_mixed():
    """Mixed movies: existing and new"""
    return [
        {"id": 1, "title": "Existing Movie", "inCinemas": "2023-01-01T00:00:00Z"},
        {"id": 2, "title": "New Movie", "inCinemas": "2023-02-01T00:00:00Z"},
    ]


# --- Хелперы для моков SQLAlchemy-запросов ---
@pytest.fixture
def mock_exists_result_false():
    """Мок результата select(exists().where(...)) => False"""
    mock_result = Mock()
    mock_result.scalar.return_value = False
    return mock_result


@pytest.fixture
def mock_exists_result_true():
    """Мок результата select(exists().where(...)) => True"""
    mock_result = Mock()
    mock_result.scalar.return_value = True
    return mock_result


@pytest.fixture
def setup_mock_session_exists_check(
    mock_session, mock_exists_result_false, mock_exists_result_true
):
    """Фабрика для настройки проверки существования фильмов"""

    def _setup(exists_sequence=None):
        if exists_sequence is None:
            exists_sequence = [False]  # по умололчанию все фильмы новые

        mock_result = Mock()
        if len(exists_sequence) == 1:
            mock_result.scalar.return_value = exists_sequence[0]
        else:
            mock_result.scalar.side_effect = exists_sequence

        mock_session.execute.return_value = mock_result
        return mock_session

    return _setup


# --- Хелпер для мокирования fetch_radarr_movies ---
@pytest.fixture
def mock_fetch_radarr_movies():
    """Фикстура для мока функции fetch_radarr_movies"""
    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        yield mock_fetch
