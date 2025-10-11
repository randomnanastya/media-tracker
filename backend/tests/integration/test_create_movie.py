import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select
import asyncio

from app.database import get_session
from app.main import app
from app.models import Base, Media, Movie, MediaType
from tests.utils.db_asserts import assert_model_matches

TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/test"

@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    yield engine
    await engine.dispose()

async def wait_for_db(engine):
    """Wait for the database to become available."""
    while True:
        try:
            connection = await engine.connect()
            await connection.close()
            break
        except Exception as e:
            print(f"Waiting for DB: {e}")
            await asyncio.sleep(1)

@pytest.fixture(scope="session", autouse=True)
async def create_tables(test_engine):
    await wait_for_db(test_engine)  # Wait until DB is ready
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # Drop first to ensure clean state
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def test_session(test_engine):
    connection = await test_engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection)
    yield session
    await session.close()
    await transaction.rollback()
    await connection.close()

@pytest.fixture
def override_get_session(test_session):
    async def _override_get_session():
        return test_session
    app.dependency_overrides[get_session] = _override_get_session
    yield
    app.dependency_overrides.pop(get_session, None)

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_import_radarr_movies_new_movie(client, test_session, override_get_session, monkeypatch):
    # Mock the fetch_radarr_movies function
    mock_movies = [
        {
            "id": 123,
            "title": "Test Movie",
            "inCinemas": "2023-01-01T00:00:00Z",
            "year": 2010
        }
    ]
    mock_fetch = AsyncMock(return_value=mock_movies)
    monkeypatch.setattr("app.services.radarr_service.fetch_radarr_movies", mock_fetch)

    # Call the API endpoint
    response = await client.post("/api/v1/radarr/import")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "imported": 1}

    # Verify data in the database
    media_result = await test_session.execute(select(Media).where(Media.title == "Test Movie"))
    media = media_result.scalar_one_or_none()
    assert media is not None

    assert_model_matches(
        media,
        expected={
            "title": mock_movies[0]["title"],
            "type": MediaType.MOVIE,
        },
        exclude={"id", "created_at", "updated_at", "release_date"}
    )

    movie_result = await test_session.execute(select(Movie).where(Movie.radarr_id == 123))
    movie = movie_result.scalar_one_or_none()
    assert movie is not None

    assert_model_matches(
        movie,
        expected={
            "id": media.id,
            "radarr_id": mock_movies[0]["id"],
            "watched": False,
        },
        exclude={"watched_at"}
    )

@pytest.mark.asyncio
async def test_import_radarr_movies_existing_movie(client, test_session, override_get_session, monkeypatch):
    # First, insert an existing movie manually
    existing_media = Media(
        type=MediaType.MOVIE,
        title="Existing Movie",
        release_date=None
    )
    test_session.add(existing_media)
    await test_session.flush()

    existing_movie = Movie(
        id=existing_media.id,
        radarr_id=456,
        watched=False,
        watched_at=None
    )
    test_session.add(existing_movie)
    await test_session.commit()  # Commit this setup data (will be rolled back after test)

    # Mock the fetch_radarr_movies to return the existing movie
    mock_movies = [
        {
            "id": 456,
            "title": "Existing Movie",
            "inCinemas": None
        }
    ]
    mock_fetch = AsyncMock(return_value=mock_movies)
    monkeypatch.setattr("app.services.radarr_service.fetch_radarr_movies", mock_fetch)

    # Call the API endpoint
    response = await client.post("/api/v1/radarr/import")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "imported": 0}  # No new import

    # Verify no new data was added
    movie_count = await test_session.execute(select(Movie))
    assert len(movie_count.scalars().all()) == 1  # Only the existing one

@pytest.mark.asyncio
async def test_import_radarr_movies_invalid_data(client, test_session, override_get_session, monkeypatch):
    # Mock the fetch_radarr_movies to return invalid movie (no id)
    mock_movies = [
        {
            "title": "Invalid Movie"  # No 'id'
        }
    ]
    mock_fetch = AsyncMock(return_value=mock_movies)
    monkeypatch.setattr("app.services.radarr_service.fetch_radarr_movies", mock_fetch)

    # Call the API endpoint
    response = await client.post("/api/v1/radarr/import")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "imported": 0}  # Skipped

    # Verify no data in the database
    media_count = await test_session.execute(select(Media))
    assert len(media_count.scalars().all()) == 0