from datetime import datetime, timezone
from sqlalchemy import select
import logging

from app.database import AsyncSessionLocal
from app.models import Media, Movie, MediaType
from app.client.radarr_client import fetch_radarr_movies

logger = logging.getLogger(__name__)

async def import_radarr_movies() -> int:
    """Imports movies from Radarr into the database with logging and aware datetime."""
    try:
        movies = await fetch_radarr_movies()
    except Exception as e:
        logger.error("Failed to fetch data from Radarr: %s", e)
        raise

    imported = 0

    async with AsyncSessionLocal() as session:
        for m in movies:
            radarr_id = m.get("id")  # Radarr movie ID
            if not radarr_id:
                logger.warning("Skipping movie without Radarr ID: %s", m.get("title"))
                continue

            # Check if the movie already exists by radarr_id
            exists = await session.execute(
                select(Movie).where(Movie.radarr_id == radarr_id)
            )
            if exists.scalars().first():
                continue  # skip already added

            # Handle release date with timezone
            release_date = None
            if m.get("inCinemas"):
                try:
                    release_date = datetime.fromisoformat(m["inCinemas"])
                    if release_date.tzinfo is None:
                        release_date = release_date.replace(tzinfo=timezone.utc)
                    else:
                        release_date = release_date.astimezone(timezone.utc)
                except Exception as e:
                    logger.error(
                        "Failed to parse release date for movie '%s': %s",
                        m.get("title"),
                        e
                    )
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
                logger.error(
                    "Failed to insert movie '%s' into the database: %s",
                    m.get("title"),
                    e
                )
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
