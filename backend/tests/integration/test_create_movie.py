from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.database import get_session
from app.main import app
from app.models import Base, Media, MediaType, Movie
from tests.utils.db_asserts import assert_model_matches

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
    async with AsyncSession(engine_for_test) as session:
        yield session


@pytest.fixture
async def client_with_db(session_for_test):
    async def override_get_session():
        yield session_for_test

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_import_radarr_movies_new_movie(
    client_with_db, session_for_test, monkeypatch  # ← используем правильные названия фикстур
):
    client = client_with_db  # ← client_with_db возвращает только client

    # Mock the fetch_radarr_movies function
    mock_movies = [
        {"id": 123, "title": "Test Movie", "inCinemas": "2023-01-01T00:00:00Z", "year": 2010}
    ]
    mock_fetch = AsyncMock(return_value=mock_movies)
    monkeypatch.setattr("app.services.radarr_service.fetch_radarr_movies", mock_fetch)

    # Call the API endpoint
    response = await client.post("/api/v1/radarr/import")
    assert response.status_code == 200
    assert response.json() == {"status": "success", "imported_count": 1}

    # Verify data in the database
    media_result = await session_for_test.execute(select(Media).where(Media.title == "Test Movie"))
    media = media_result.scalar_one_or_none()
    assert media is not None

    assert_model_matches(
        media,
        expected={
            "title": mock_movies[0]["title"],
            "media_type": MediaType.MOVIE,
        },
        exclude={"id", "created_at", "updated_at", "release_date"},
    )

    movie_result = await session_for_test.execute(select(Movie).where(Movie.radarr_id == 123))
    movie = movie_result.scalar_one_or_none()
    assert movie is not None

    assert_model_matches(
        movie,
        expected={
            "id": media.id,
            "radarr_id": mock_movies[0]["id"],
            "watched": False,
        },
        exclude={"watched_at"},
    )


@pytest.mark.asyncio
async def test_import_radarr_movies_existing_movie(client_with_db, session_for_test, monkeypatch):
    # First, insert an existing movie manually
    existing_media = Media(media_type=MediaType.MOVIE, title="Existing Movie", release_date=None)
    session_for_test.add(existing_media)
    await session_for_test.flush()

    existing_movie = Movie(id=existing_media.id, radarr_id=456, watched=False, watched_at=None)
    session_for_test.add(existing_movie)
    await session_for_test.commit()  # Commit this setup data (will be rolled back after test)

    # Mock the fetch_radarr_movies to return the existing movie
    mock_movies = [{"id": 456, "title": "Existing Movie", "inCinemas": None}]
    mock_fetch = AsyncMock(return_value=mock_movies)
    monkeypatch.setattr("app.services.radarr_service.fetch_radarr_movies", mock_fetch)

    # Call the API endpoint
    response = await client_with_db.post("/api/v1/radarr/import")
    assert response.status_code == 200
    assert response.json() == {"status": "success", "imported_count": 0}  # No new import

    # Verify no new data was added
    movie_count = await session_for_test.execute(select(Movie))
    assert len(movie_count.scalars().all()) == 1  # Only the existing one


@pytest.mark.asyncio
async def test_import_radarr_movies_invalid_data(client_with_db, session_for_test, monkeypatch):
    # Mock the fetch_radarr_movies to return invalid movie (no id)
    mock_movies = [{"title": "Invalid Movie"}]  # No 'id'
    mock_fetch = AsyncMock(return_value=mock_movies)
    monkeypatch.setattr("app.services.radarr_service.fetch_radarr_movies", mock_fetch)

    # Call the API endpoint
    response = await client_with_db.post("/api/v1/radarr/import")
    assert response.status_code == 200
    assert response.json() == {"status": "success", "imported_count": 0}  # Skipped

    # Verify no data in the database
    media_count = await session_for_test.execute(select(Media))
    assert len(media_count.scalars().all()) == 0
