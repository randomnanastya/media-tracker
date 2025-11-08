from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.client.jellyfin_client import fetch_jellyfin_movies
from app.config import logger
from app.models import Media, MediaType, Movie
from app.schemas.jellyfin import JellyfinImportMoviesResponse
from app.services.movie_utils import (
    find_movie_by_external_ids,
    find_movie_by_jellyfin_id,
    parse_release_date,
)


def _update_existing_movie(
    movie: Movie,
    jellyfin_id: str | None,
    tmdb_id: str | None,
    imdb_id: str | None,
    release_date: datetime | None,
    title: str,
) -> bool:
    """Update existing movie and return True if any changes were made."""
    was_updated = False

    # Update jellyfin_id only if present and different
    if jellyfin_id and movie.jellyfin_id != jellyfin_id:
        movie.jellyfin_id = jellyfin_id
        was_updated = True

    # Update tmdb_id only if not already set
    if tmdb_id and not movie.tmdb_id:
        movie.tmdb_id = tmdb_id
        was_updated = True

    # Update imdb_id only if not already set
    if imdb_id and not movie.imdb_id:
        movie.imdb_id = imdb_id
        was_updated = True

    # Update release_date only if media exists and release_date is missing
    if release_date and movie.media and movie.media.release_date is None:
        movie.media.release_date = release_date
        was_updated = True

    if was_updated:
        logger.info("Updated movie '%s' with new data from Jellyfin", title)

    return was_updated


async def _create_new_movie(
    session: AsyncSession,
    title: str,
    jellyfin_id: str | None,
    tmdb_id: str | None,
    imdb_id: str | None,
    release_date: datetime | None,
) -> None:
    """Create a new movie with associated Media entry."""
    media_obj = Media(
        media_type=MediaType.MOVIE,
        title=title,
        release_date=release_date,
    )
    session.add(media_obj)
    await session.flush()

    movie_obj = Movie(
        id=media_obj.id,
        jellyfin_id=jellyfin_id,
        tmdb_id=tmdb_id,
        imdb_id=imdb_id,
    )
    session.add(movie_obj)

    id_info = []
    if jellyfin_id:
        id_info.append(f"jellyfin_id={jellyfin_id}")
    if tmdb_id:
        id_info.append(f"tmdb={tmdb_id}")
    if imdb_id:
        id_info.append(f"imdb={imdb_id}")

    logger.info("Added new movie: %s (%s) from Jellyfin", title, ", ".join(id_info))


async def import_jellyfin_movies(session: AsyncSession) -> JellyfinImportMoviesResponse:
    """Import movies from Jellyfin into the database."""
    movies = await fetch_jellyfin_movies()
    imported = 0
    updated = 0

    try:
        for movie_data in movies:
            jellyfin_id_raw = movie_data.get("Id")
            jellyfin_id = str(jellyfin_id_raw) if jellyfin_id_raw is not None else None
            title = movie_data.get("Name", "Unknown Title")
            release_date = parse_release_date(movie_data.get("PremiereDate"), title)
            tmdb_id_raw = movie_data.get("ProviderIds", {}).get("Tmdb")
            tmdb_id = str(tmdb_id_raw) if tmdb_id_raw is not None else None
            imdb_id_raw = movie_data.get("ProviderIds", {}).get("Imdb")
            imdb_id = str(imdb_id_raw) if imdb_id_raw is not None else None

            # Skip if no identifiers are provided
            if not jellyfin_id and not tmdb_id and not imdb_id:
                logger.warning("Skipping movie without any IDs: %s", title)
                continue

            existing_movie = None

            # 1. First, search by jellyfin_id (if available)
            if jellyfin_id:
                existing_movie = await find_movie_by_jellyfin_id(session, jellyfin_id)

            # 2. If not found by jellyfin_id, search by external IDs
            if not existing_movie:
                existing_movie = await find_movie_by_external_ids(session, tmdb_id, imdb_id)

            # 3. Update existing movie
            if existing_movie:
                if _update_existing_movie(
                    existing_movie,
                    jellyfin_id,
                    tmdb_id,
                    imdb_id,
                    release_date,
                    title,
                ):
                    updated += 1
            else:
                # 4. Create new movie
                await _create_new_movie(
                    session,
                    title,
                    jellyfin_id,
                    tmdb_id,
                    imdb_id,
                    release_date,
                )
                imported += 1

        await session.commit()

    except Exception as e:
        logger.error("Failed to commit session: %s", e)
        await session.rollback()
        raise

    logger.info("Jellyfin import completed: %d imported, %d updated", imported, updated)
    return JellyfinImportMoviesResponse(imported_count=imported, updated_count=updated)
