from datetime import UTC, datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.radarr_client import fetch_radarr_movies
from app.core.logging import logger
from app.models import Media, MediaType, Movie


async def import_radarr_movies(session: AsyncSession) -> int:
    """Imports movies from Radarr into the database with logging and aware datetime."""
    try:
        movies = await fetch_radarr_movies()
    except Exception as e:
        logger.error("Failed to fetch data from Radarr: %s", e)
        raise

    imported = 0

    for m in movies:
        radarr_id = m.get("id")
        if not radarr_id:
            logger.warning("Skipping movie without Radarr ID: %s", m.get("title"))
            continue

        from sqlalchemy import exists

        result = await session.execute(select(exists().where(Movie.radarr_id == radarr_id)))
        movie_exists: bool = cast(bool, result.scalar())

        if movie_exists:
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
                logger.error("Failed to parse release date for movie '%s': %s", m.get("title"), e)
                release_date = None

        try:
            media_obj = Media(
                type=MediaType.MOVIE,
                title=m.get("title", "Unknown Title"),
                release_date=release_date,
            )
            session.add(media_obj)
            await session.flush()

            movie_obj = Movie(
                id=media_obj.id,
                radarr_id=radarr_id,
                watched=False,
                watched_at=None,
            )
            session.add(movie_obj)

            imported += 1
        except Exception as e:
            logger.error("Failed to insert movie '%s' into the database: %s", m.get("title"), e)
            await session.rollback()
            continue

    try:
        await session.commit()
    except Exception as e:
        logger.error("Failed to commit session: %s", e)
        await session.rollback()
        raise

    logger.info("Imported %d movies from Radarr", imported)
    return imported
