import os
from collections.abc import AsyncGenerator, Callable, Coroutine, Generator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from httpx import AsyncClient
from pytest_factoryboy import register

from app.dependencies.auth import get_current_user
from app.main import app
from app.models import AppUser, Movie, Series, User, WatchHistory
from tests.factories import (
    AppUserFactory,
    EpisodeFactory,
    MediaFactory,
    MovieFactory,
    RadarrMovieDictFactory,
    RefreshTokenFactory,
    SeasonFactory,
    SeriesFactory,
    UserFactory,
    WatchHistoryFactory,
)

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

_scheduler_patcher = patch("apscheduler.schedulers.asyncio.AsyncIOScheduler")
_mock_scheduler = _scheduler_patcher.start()
_mock_scheduler_instance = MagicMock()
_mock_scheduler_instance.start = MagicMock()
_mock_scheduler.return_value = _mock_scheduler_instance


# Pytest hook для очистки patcher в конце тестовой сессии
def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    """Останавливаем patcher после завершения всех тестов."""
    _scheduler_patcher.stop()


# === pytest-factoryboy регистрация ===
# Регистрация модельных фабрик для автоматических фикстур
# После регистрации доступны фикстуры: media_factory, media, movie_factory, movie, и т.д.

register(MediaFactory)
register(MovieFactory)
register(SeriesFactory)
register(SeasonFactory)
register(EpisodeFactory)
register(UserFactory)
register(WatchHistoryFactory)
register(AppUserFactory)
register(RefreshTokenFactory)


@pytest.fixture
def mock_current_user() -> AppUser:
    return AppUserFactory.build(id=1, username="testadmin", is_active=True)


@pytest.fixture(autouse=True)
def override_auth_dependency(mock_current_user: AppUser) -> Generator[None, None, None]:
    async def override() -> AppUser:
        return mock_current_user

    app.dependency_overrides[get_current_user] = override
    yield
    app.dependency_overrides.pop(get_current_user, None)


# --- Моки базы данных и зависимостей ---
@pytest.fixture
def mock_session() -> AsyncMock:
    """Асинхронный мок SQLAlchemy-сессии"""
    mock = AsyncMock()
    mock.add = Mock()
    mock.flush = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    mock.execute = AsyncMock()
    return mock


@pytest.fixture
def override_session_dependency(mock_session: AsyncMock) -> Generator[None, None, None]:
    """Переопределение FastAPI зависимости get_session"""

    async def override_get_session() -> AsyncGenerator[AsyncMock, None]:
        yield mock_session

    from app.database import get_session
    from app.main import app

    app.dependency_overrides[get_session] = override_get_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(override_session_dependency: None) -> AsyncGenerator[AsyncClient, None]:
    """HTTP-клиент для тестирования API"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_scalar_result() -> Callable[[Any | None], Mock]:
    """Фабрика для создания моков скалярных результатов запросов."""

    def _mock(first_value: Any | None = None) -> Mock:
        mock_result = Mock()
        mock_scalar = Mock()
        mock_scalar.first.return_value = first_value
        mock_result.scalars.return_value = mock_scalar
        return mock_result

    return _mock


@pytest.fixture
def clear_env() -> Generator[None, None, None]:
    """Очищаем только специфичные переменные окружения приложения.

    Используйте эту фикстуру явно в тестах, где нужна полная изоляция от env vars.
    autouse=True убран, так как полная очистка os.environ ломает системные переменные.
    """
    # Очищаем только переменные приложения, не трогая системные (PATH, HOME, и т.д.)
    app_env_keys = [
        "RADARR_URL",
        "RADARR_API_KEY",
        "SONARR_URL",
        "SONARR_API_KEY",
        "JELLYFIN_URL",
        "JELLYFIN_API_KEY",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "APP_ENV",
    ]

    original_values: dict[str, str | None] = {key: os.environ.get(key) for key in app_env_keys}

    # Очищаем только переменные приложения
    for key in app_env_keys:
        os.environ.pop(key, None)

    yield

    # Восстанавливаем оригинальные значения
    for key, value in original_values.items():
        if value is not None:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)


@pytest.fixture
def mock_httpx_client() -> Generator[Mock, None, None]:
    """Мокаем httpx.AsyncClient."""
    with patch("httpx.AsyncClient") as mock_client:
        yield mock_client


@pytest.fixture
def mock_env_vars() -> Callable[..., Any]:
    """Мокаем переменные окружения для клиентов API."""

    def _mock(**env_vars: str) -> Any:
        """
        Патчит os.getenv для возврата указанных значений.

        Пример использования:
            with mock_env_vars(JELLYFIN_URL="http://jf.local", JELLYFIN_API_KEY="abc123"):
                result = await fetch_jellyfin_movies()
        """

        def mock_getenv(key: str, default: str | None = None) -> str | None:
            return env_vars.get(key, default)

        return patch("os.getenv", side_effect=mock_getenv)

    return _mock


@pytest.fixture
def mock_db_result() -> Mock:
    """Мок результата выполнения DB запроса."""
    mock_result = Mock()
    mock_scalars = Mock()
    mock_scalars.first.return_value = None
    mock_result.scalars.return_value = mock_scalars
    return mock_result


@pytest.fixture
def radarr_movies_basic() -> list[dict[str, Any]]:
    """Базовый список фильмов из Radarr."""
    movies: list[dict[str, Any]] = [  # type: ignore[return-value]
        RadarrMovieDictFactory(id=1, inCinemas="2024-01-01T00:00:00Z"),
        RadarrMovieDictFactory(id=2, inCinemas="2023-02-01T00:00:00Z"),
        RadarrMovieDictFactory(id=3, no_date=True),
    ]
    return movies


# radarr_movies_invalid_data fixture removed - unused
# For invalid data tests use RadarrMovieDictFactory with traits:
# RadarrMovieDictFactory.build(missing_id=True, invalid_date=True)


@pytest.fixture
def radarr_movies_without_radarr_id() -> list[dict[str, Any]]:
    """List of movies - one valid, one without any IDs (will be skipped)."""

    movies: list[dict[str, Any]] = [  # type: ignore[return-value]
        RadarrMovieDictFactory(id=1, title="Movie with radarr ID"),
        RadarrMovieDictFactory(id=None, title="Movie without any IDs", no_external_ids=True),
    ]
    return movies


@pytest.fixture
def radarr_movies_large_list() -> list[dict[str, Any]]:
    return RadarrMovieDictFactory.create_batch(20)


@pytest.fixture
def existing_movie_complete() -> Movie:
    """Фильм со всеми заполненными ID."""
    return MovieFactory.build(
        id=3,
        radarr_id=123,
        tmdb_id="27205",
        imdb_id="tt1375666",
        jellyfin_id="jf-inception",
        media__id=3,
        media__title="Inception",
        media__release_date=datetime(2010, 7, 16, tzinfo=UTC),
    )


@pytest.fixture
def existing_movie_without_ids() -> Movie:
    """Фильм без внешних ID."""
    return MovieFactory.build(
        id=1,
        jellyfin_id=None,
        tmdb_id=None,
        imdb_id=None,
        radarr_id=None,
        media__id=1,
        media__title="Inception",
        media__release_date=None,
    )


# Фикстуры setup_movie_mocked_* удалены - имели побочные эффекты (mock_session.add)
# Создавайте объекты через MovieFactory и явно добавляйте в session:
#   movie = MovieFactory.build(...)
#   mock_session.add(movie.media)


# @pytest.fixture
# def radarr_movies_from_json() -> list[dict[str, Any]]:
#     """Фильмы из JSON файла."""
#     path = pathlib.Path(__file__).parent / "fixtures" / "data" / "movies.json"
#     with open(path, encoding="utf-8") as f:
#         return json.load(f)


# @pytest.fixture
# def movie() -> Movie:
#     """Базовый объект Movie для тестирования."""
#     movie = Movie(
#         id=10,
#         jellyfin_id="jf-movie-1",
#         tmdb_id="123",
#         imdb_id="tt123",
#     )
#     return movie


@pytest.fixture
def existing_watch(movie: Movie, user: User) -> WatchHistory:
    """История просмотров фильма для пользователя."""
    return WatchHistory(
        user_id=user.id,
        media_id=movie.id,
        episode_id=None,
        is_watched=True,
        watched_at=None,
    )


# Фикстура sonarr_series_from_json удалена - используйте SeriesDictFactory.build_batch()


# sample_movies_* fixtures removed - use RadarrMovieDictFactory.build() instead
# Example: RadarrMovieDictFactory.build(id=1, title="Movie", inCinemas="2023-01-01T00:00:00Z")


# --- Моки серий и эпизодов из Sonarr ---
@pytest.fixture
def sonarr_series_basic() -> list[dict[str, Any]]:
    """Базовые серии из Sonarr API."""
    from tests.factories import SeriesDictFactory

    return [
        SeriesDictFactory.build(
            id=1,
            title="Test Series 1",
            imdbId="tt1234567",
            firstAired="2020-01-01",
            year=2020,
            status="continuing",
            images=[{"coverType": "poster", "remoteUrl": "http://example.com/poster.jpg"}],
            genres=["Drama", "Sci-Fi"],
            rating={"value": 8.5, "votes": 1000},
        ),
        SeriesDictFactory.build(
            id=2,
            title="Test Series 2",
            imdbId="tt7654321",
            firstAired="2021-02-01",
            year=2021,
            status="ended",  # ended
            images=[],
            genres=["Comedy"],
            rating={"value": 7.0, "votes": 500},
        ),
    ]


@pytest.fixture
def sonarr_episodes_basic() -> list[dict[str, Any]]:
    """Базовые эпизоды из Sonarr API."""
    from tests.factories import SonarrEpisodeDictFactory

    return [
        SonarrEpisodeDictFactory.build(
            id=101,
            seriesId=1,
            seasonNumber=1,
            episodeNumber=1,
            title="Pilot",
            airDateUtc="2020-01-01T00:00:00Z",
            overview="The pilot episode.",
        ),
        SonarrEpisodeDictFactory.build(
            id=102,
            seriesId=1,
            seasonNumber=1,
            episodeNumber=2,
            title="Episode 2",
            airDateUtc="2020-01-08T00:00:00Z",
            overview="The second episode.",
        ),
    ]


@pytest.fixture
def sonarr_series_invalid_data() -> list[dict[str, Any]]:
    """Серии с невалидными данными."""
    from tests.factories import SeriesDictFactory

    return [
        SeriesDictFactory.build(
            id=101,
            title="Pilot",
            invalid_date=True,  # использует trait invalid_date
        )
    ]


@pytest.fixture
def existing_series_without_ids() -> Series:
    """Серия без внешних ID."""
    return SeriesFactory.build(
        id=1,
        jellyfin_id=None,
        tvdb_id=None,
        imdb_id=None,
        tmdb_id=None,
        sonarr_id=None,
        status=None,
        year=None,
        media__id=1,
        media__title="Old title",
        media__release_date=None,
    )


# Фикстуры series, season, episode удалены - используйте автофикстуры pytest-factoryboy
# Доступны: series, season, episode (instance) и series_factory, season_factory, episode_factory


@pytest.fixture
def empty_scalars() -> Callable[..., Coroutine[Any, Any, list[Any]]]:
    async def _scalars(*args: Any, **kwargs: Any) -> list[Any]:
        return []

    return _scalars


# Фикстура user удалена - используйте автофикстуру pytest-factoryboy
# Доступны: user (instance) и user_factory


@pytest.fixture
def mock_exists_false() -> Mock:
    """Мок для select(exists()) → False"""
    m = Mock()
    m.scalar.return_value = False
    return m


@pytest.fixture
def mock_exists_true() -> Mock:
    """Мок для select(exists()) → True"""
    m = Mock()
    m.scalar.return_value = True
    return m


@pytest.fixture
def setup_mock_session_exists_check(
    mock_session: AsyncMock, mock_exists_false: Mock, mock_exists_true: Mock
) -> Callable[[list[bool] | None], AsyncMock]:
    """Фабрика для настройки проверки существования фильмов"""

    def _setup(exists_sequence: list[bool] | None = None) -> AsyncMock:
        if exists_sequence is None:
            exists_sequence = [False]

        mock_result = Mock()
        if len(exists_sequence) == 1:
            mock_result.scalar.return_value = exists_sequence[0]
        else:
            mock_result.scalar.side_effect = exists_sequence

        mock_session.execute.return_value = mock_result
        return mock_session

    return _setup


# --- Хелперы для мокирования fetch_radarr_movies и fetch_sonarr_series ---
@pytest.fixture
def mock_fetch_radarr_movies() -> Generator[AsyncMock, None, None]:
    """Фикстура для мока функции fetch_radarr_movies"""
    with patch(
        "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
    ) as mock_fetch:
        yield mock_fetch


@pytest.fixture
def mock_fetch_sonarr_series() -> Generator[AsyncMock, None, None]:
    """Фикстура для мока функции fetch_sonarr_series"""
    with patch(
        "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
    ) as mock_fetch:
        yield mock_fetch


@pytest.fixture
def mock_fetch_sonarr_episodes() -> Generator[AsyncMock, None, None]:
    """Фикстура для мока функции fetch_sonarr_episodes"""
    with patch(
        "app.services.sonarr_service.fetch_sonarr_episodes", new_callable=AsyncMock
    ) as mock_fetch:
        yield mock_fetch
