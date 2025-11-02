from datetime import UTC, datetime
from typing import cast

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.radarr_client import fetch_radarr_movies
from app.config import logger
from app.models import Media, MediaType, Movie
from app.schemas.radarr import RadarrImportResponse


async def import_radarr_movies(session: AsyncSession) -> RadarrImportResponse:
    """Imports movies from Radarr into the database with logging and aware datetime."""
    movies = await fetch_radarr_movies()  # Let RadarrClientError propagate to handlers.py
    imported = 0

    for m in movies:
        radarr_id = m.get("id")
        title = m.get("title", "Unknown Title")

        if not radarr_id:
            logger.warning("Skipping movie without Radarr ID: %s", title)
            continue

        release_date = None
        if m.get("inCinemas"):
            try:
                release_date = datetime.fromisoformat(m["inCinemas"])
                if release_date.tzinfo is None:
                    release_date = release_date.replace(tzinfo=UTC)
                else:
                    release_date = release_date.astimezone(UTC)
            except Exception as e:
                logger.error("Failed to parse release date for movie '%s': %s", title, e)

        result = await session.execute(select(exists().where(Movie.radarr_id == radarr_id)))
        movie_exists: bool = cast(bool, result.scalar())
        if movie_exists:
            continue

        try:
            media_obj = Media(
                media_type=MediaType.MOVIE,
                title=title,
                release_date=release_date,
            )
            session.add(media_obj)
            await session.flush()

            tmdb_id = str(m.get("tmdbId")) if m.get("tmdbId") else None
            imdb_id = m.get("imdbId") if m.get("imdbId") else None

            movie_obj = Movie(
                id=media_obj.id,
                radarr_id=radarr_id,
                tmdb_id=tmdb_id,
                imdb_id=imdb_id,
                watched=False,
                watched_at=None,
            )
            session.add(movie_obj)

            imported += 1
        except Exception as e:
            logger.error("Failed to insert movie '%s' into the database: %s", title, e)
            await session.rollback()
            continue

    try:
        await session.commit()
    except Exception as e:
        logger.error("Failed to commit session: %s", e)
        await session.rollback()
        raise

    logger.info("Imported %d movies from Radarr", imported)
    return RadarrImportResponse(imported_count=imported)
