from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Media, MediaType, Movie
from app.schemas.jellyfin import JellyfinImportMoviesResponse


@pytest.mark.asyncio
async def test_import_jellyfin_movies_new_movie(
    client_with_db,
    session_for_test,
    monkeypatch,
):
    mock_movies = [
        {
            "Id": "jf-123",
            "Name": "Jellyfin Movie",
            "PremiereDate": "2022-05-01T00:00:00Z",
            "CommunityRating": 7.171,
            "ProviderIds": {
                "Tmdb": "111",
                "Imdb": "tt1111111",
            },
        }
    ]

    mock_fetch = AsyncMock(return_value=mock_movies)
    monkeypatch.setattr(
        "app.services.import_jellyfin_movies_service.fetch_jellyfin_movies",
        mock_fetch,
    )

    act_resp = await client_with_db.post("/api/v1/jellyfin/import/movies")
    assert act_resp.status_code == 200

    exp_resp = JellyfinImportMoviesResponse(
        imported_count=1,
        updated_count=0,
    )
    assert act_resp.json() == exp_resp.model_dump(mode="json", exclude_none=True)

    media_result = await session_for_test.execute(
        select(Media).where(Media.title == "Jellyfin Movie")
    )
    media = media_result.scalar_one()
    assert media.media_type == MediaType.MOVIE
    assert media.release_date is not None

    movie_result = await session_for_test.execute(
        select(Movie).where(Movie.jellyfin_id == "jf-123")
    )
    act_movie = movie_result.scalar_one()

    assert act_movie.id == media.id
    assert act_movie.tmdb_id == mock_movies[0].get("ProviderIds").get("Tmdb")
    assert act_movie.imdb_id == mock_movies[0].get("ProviderIds").get("Imdb")
    assert act_movie.jellyfin_id == mock_movies[0].get("Id")


@pytest.mark.asyncio
async def test_import_jellyfin_movies_updates_existing_movie_by_tmdb(
    client_with_db,
    session_for_test,
    monkeypatch,
):
    # existing movie from Radarr
    media = Media(
        media_type=MediaType.MOVIE,
        title="Existing Movie",
    )
    session_for_test.add(media)
    await session_for_test.flush()

    movie = Movie(
        id=media.id,
        tmdb_id="222",
        imdb_id=None,
        jellyfin_id=None,
        status="released",
    )
    session_for_test.add(movie)
    await session_for_test.commit()

    mock_movies = [
        {
            "Id": "jf-222",
            "Name": "Existing Movie",
            "PremiereDate": "2015-03-21T00:00:00Z",
            "ProviderIds": {
                "Tmdb": "222",
                "Imdb": "tt2222222",
            },
        }
    ]

    mock_fetch = AsyncMock(return_value=mock_movies)
    monkeypatch.setattr(
        "app.services.import_jellyfin_movies_service.fetch_jellyfin_movies",
        mock_fetch,
    )

    act_resp = await client_with_db.post("/api/v1/jellyfin/import/movies")
    assert act_resp.status_code == 200

    exp_resp = JellyfinImportMoviesResponse(
        imported_count=0,
        updated_count=1,
    )
    assert act_resp, exp_resp

    # still only one movie
    movies_result = await session_for_test.execute(select(Movie).options(selectinload(Movie.media)))
    movies = movies_result.scalars().all()
    assert len(movies) == 1

    updated_movie = movies[0]
    assert updated_movie.jellyfin_id == mock_movies[0].get("Id")
    assert updated_movie.imdb_id == mock_movies[0].get("ProviderIds").get("Imdb")

    assert updated_movie.tmdb_id == mock_movies[0].get("ProviderIds").get("Tmdb")
    # release_date updated via media
    assert updated_movie.media.release_date is not None


@pytest.mark.asyncio
async def test_import_jellyfin_movies_skip_movie_without_ids(
    client_with_db,
    session_for_test,
    monkeypatch,
):
    mock_movies = [
        {
            "Id": None,
            "Name": "Broken Movie",
            "PremiereDate": None,
            "ProviderIds": {},
        }
    ]

    mock_fetch = AsyncMock(return_value=mock_movies)
    monkeypatch.setattr(
        "app.services.import_jellyfin_movies_service.fetch_jellyfin_movies",
        mock_fetch,
    )

    act_resp = await client_with_db.post("/api/v1/jellyfin/import/movies")
    assert act_resp.status_code == 200

    assert act_resp.json() == JellyfinImportMoviesResponse(
        imported_count=0, updated_count=0
    ).model_dump(mode="json", exclude_none=True)

    media_result = await session_for_test.execute(select(Media))
    assert media_result.scalars().all() == []

    movie_result = await session_for_test.execute(select(Movie))
    assert movie_result.scalars().all() == []
