from datetime import UTC, datetime
from typing import cast

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.radarr_client import fetch_radarr_movies
from app.config import logger
from app.models import Media, MediaType, Movie
from app.schemas.error_codes import RadarrErrorCode
from app.schemas.radarr import RadarrImportResponse
from app.schemas.responses import ErrorDetail


async def import_radarr_movies(session: AsyncSession) -> RadarrImportResponse:
    """Imports movies from Radarr into the database with logging and aware datetime."""
    try:
        movies = await fetch_radarr_movies()
    except httpx.RequestError as e:
        logger.error("Network error fetching Radarr movies: %s", str(e))
        raise HTTPException(
            status_code=502,
            detail=ErrorDetail(
                code=RadarrErrorCode.NETWORK_ERROR,
                message=f"Network error: {e!s}",
            ).model_dump(),
        ) from e
    except Exception as e:
        logger.error("Failed to fetch data from Radarr: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=ErrorDetail(
                code=RadarrErrorCode.RADARR_FETCH_FAILED,
                message=f"Network error: {e!s}",
            ).model_dump(),
        ) from e

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
                logger.error(
                    "Failed to parse release date for movie '%s': %s",
                    title,
                    e,
                )
                logger.warning("Skipping movie '%s' due to invalid release date", title)
                continue

        from sqlalchemy import exists

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

            movie_obj = Movie(
                id=media_obj.id,
                radarr_id=radarr_id,
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
