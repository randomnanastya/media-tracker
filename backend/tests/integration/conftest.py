import os
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.database import get_session
from app.dependencies.auth import get_current_user
from app.main import app
from app.models import AppUser, Base, MediaType, WatchStatus
from app.utils.security import hash_password
from tests.factories import (
    AppUserFactory,
    EpisodeFactory,
    MediaFactory,
    MovieFactory,
    SeasonFactory,
    SeriesFactory,
    UserFactory,
    WatchHistoryFactory,
)

TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/test"


@pytest.fixture
async def engine_for_test():
    """Function-scoped engine"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest.fixture
async def session_for_test(engine_for_test):
    """Базовая сессия для тестов."""
    async with AsyncSession(engine_for_test) as session:
        yield session


@pytest.fixture
async def session_no_expire(engine_for_test):
    """
    Сессия с отключенным expire_on_commit.
    Полезно для тестов, где объекты используются после коммита.
    """
    async with AsyncSession(
        engine_for_test, expire_on_commit=False  # Объекты не истекают после коммита
    ) as session:
        yield session


@pytest.fixture
async def client_with_db(session_for_test):
    async def override_get_session():
        yield session_for_test

    async def override_auth():
        return AppUserFactory.build(id=1, username="test_admin", is_active=True)

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_auth
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def client_with_real_auth(session_for_test):
    """Client with real auth (get_current_user not overridden)."""

    async def override_get_session():
        yield session_for_test

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


async def create_app_user(
    session: AsyncSession,
    username: str = "admin",
    password: str = "testpassword123",
) -> tuple[AppUser, str]:
    user = AppUserFactory.build(
        username=username,
        hashed_password=hash_password(password),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user, password


@pytest.fixture
async def authenticated_client(
    session_for_test: AsyncSession, engine_for_test: object
) -> AsyncGenerator[AsyncClient, None]:
    user, password = await create_app_user(session_for_test)
    username = user.username  # capture before commit
    await session_for_test.commit()

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield session_for_test

    app.dependency_overrides[get_session] = override_get_session

    with patch.dict(os.environ, {"JWT_SECRET": "test-integration-secret-32chars!!"}):
        async with AsyncClient(app=app, base_url="http://test") as client:
            login_resp = await client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": password},
            )
            token = login_resp.cookies.get("access_token")
            client.headers["Authorization"] = f"Bearer {token}"
            yield client

    app.dependency_overrides.clear()


# Хелпер-функции для создания тестовых данных
async def create_user(session, username="user", jellyfin_user_id=None):
    """Создает тестового пользователя."""
    user = UserFactory.build(username=username, jellyfin_user_id=jellyfin_user_id)
    session.add(user)
    await session.flush()
    return user


async def create_movie(session, jellyfin_id=None, tmdb_id=None, imdb_id=None, title="Movie"):
    """Создает тестовый фильм."""
    media = MediaFactory(media_type=MediaType.MOVIE, title=title)
    session.add(media)
    await session.flush()
    movie = MovieFactory.build(
        id=media.id, jellyfin_id=jellyfin_id, tmdb_id=tmdb_id, imdb_id=imdb_id, media=media
    )

    session.add(movie)
    media.movie = movie
    await session.flush()
    return movie


async def create_watch_history(
    session, user_id, media_id, status: WatchStatus = WatchStatus.PLANNED, watched_at=None
):
    """Создает запись истории просмотров."""
    wh = WatchHistoryFactory.build(
        user_id=user_id,
        media_id=media_id,
        episode_id=None,
        status=status,
        watched_at=watched_at,
    )
    session.add(wh)
    await session.flush()
    return wh


async def create_series(session, jellyfin_id=None, tmdb_id=None, imdb_id=None, title="Series"):
    """Создает тестовый сериал."""
    media = MediaFactory(media_type=MediaType.SERIES, title=title)
    session.add(media)
    await session.flush()

    series = SeriesFactory(
        id=media.id, jellyfin_id=jellyfin_id, tmdb_id=tmdb_id, imdb_id=imdb_id, media=media
    )
    session.add(series)
    media.series = series
    await session.flush()
    return series


async def create_season(session, series_id=None, number=0, jellyfin_id=None, release_date=None):
    """Создает тестовый сезон."""
    season = SeasonFactory(
        series_id=series_id, jellyfin_id=jellyfin_id, number=number, release_date=release_date
    )
    session.add(season)
    await session.flush()
    return season


async def create_episode(session, season_id=None, number=0, jellyfin_id=None, title="Test episode"):
    """Создает тестовый эпизод."""
    season = EpisodeFactory(
        season_id=season_id, jellyfin_id=jellyfin_id, number=number, title=title
    )
    session.add(season)
    await session.flush()
    return season
