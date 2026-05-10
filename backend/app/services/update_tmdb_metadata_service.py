import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.client.tmdb_bridge_client import TmdbBridgeClientError, fetch_tmdb_movie
from app.config import logger
from app.models import Movie
from app.schemas.tmdb_bridge import TmdbBridgeMovieResponse, TmdbMetadataUpdateResponse
from app.services.movie_utils import map_tmdb_status

CONCURRENCY_LIMIT = 10


@dataclass
class _Counters:
    processed: int = field(default=0)
    updated: int = field(default=0)
    skipped: int = field(default=0)
    failed: int = field(default=0)


async def update_movies_tmdb_metadata(session: AsyncSession) -> TmdbMetadataUpdateResponse:
    query = select(Movie).where(Movie.tmdb_id.is_not(None)).options(selectinload(Movie.media))
    movies = list((await session.execute(query)).scalars().all())

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    counters = _Counters()

    async with httpx.AsyncClient() as http_client:
        await asyncio.gather(
            *[_process_one_movie(movie, semaphore, counters, http_client) for movie in movies],
            return_exceptions=True,
        )

    try:
        await session.commit()
    except Exception as e:
        logger.error("TMDB metadata update commit failed: %s", e)
        await session.rollback()
        raise

    logger.info(
        "TMDB metadata update done: processed=%d, updated=%d, skipped=%d, failed=%d",
        counters.processed,
        counters.updated,
        counters.skipped,
        counters.failed,
    )
    return TmdbMetadataUpdateResponse(
        processed_count=counters.processed,
        updated_count=counters.updated,
        skipped_count=counters.skipped,
        failed_count=counters.failed,
    )


async def _process_one_movie(
    movie: Movie,
    semaphore: asyncio.Semaphore,
    counters: _Counters,
    client: httpx.AsyncClient,
) -> None:
    async with semaphore:
        tmdb_id = movie.tmdb_id
        assert tmdb_id is not None  # guaranteed by WHERE tmdb_id IS NOT NULL
        counters.processed += 1

        try:
            raw = await fetch_tmdb_movie(tmdb_id, client=client)
        except TmdbBridgeClientError as e:
            logger.warning("Skip tmdb_id=%s due to Bridge error: %s", tmdb_id, e.message)
            counters.failed += 1
            return

        if raw is None:
            counters.skipped += 1
            return

        try:
            payload = TmdbBridgeMovieResponse.model_validate(raw)
        except Exception as e:
            logger.warning("Bridge payload validation failed for tmdb_id=%s: %s", tmdb_id, e)
            counters.failed += 1
            return

        try:
            if _apply_tmdb_update(movie, payload):
                counters.updated += 1
        except Exception as e:
            logger.error("Unexpected error applying TMDB update for tmdb_id=%s: %s", tmdb_id, e)
            counters.failed += 1


def _apply_tmdb_update(movie: Movie, payload: TmdbBridgeMovieResponse) -> bool:
    changed = False

    # title: always overwrite (TMDB is authoritative for display title)
    if payload.title and movie.media and movie.media.title != payload.title:
        movie.media.title = payload.title
        changed = True

    if payload.release_date and movie.media:
        new_dt = datetime.combine(payload.release_date, datetime.min.time()).replace(tzinfo=UTC)
        if movie.media.release_date != new_dt:
            movie.media.release_date = new_dt
            changed = True

    # fill-if-empty: keep local edits, only populate when blank
    if payload.original_title and not movie.original_title:
        movie.original_title = payload.original_title
        changed = True

    if payload.overview and not movie.overview:
        movie.overview = payload.overview
        changed = True

    if payload.backdrop_path and not movie.backdrop_path:
        movie.backdrop_path = payload.backdrop_path
        changed = True

    if payload.poster_url and not movie.poster_url:
        movie.poster_url = payload.poster_url
        changed = True

    # status: overwrite (TMDB tracks release lifecycle)
    mapped_status = map_tmdb_status(payload.status)
    if mapped_status is not None and movie.status != mapped_status:
        movie.status = mapped_status
        changed = True

    # genres: fill-if-empty
    if not movie.genres and payload.genres:
        movie.genres = [g.name for g in payload.genres]
        changed = True

    if payload.vote_average is not None and movie.rating_value != payload.vote_average:
        movie.rating_value = payload.vote_average
        changed = True

    if payload.vote_count is not None and movie.rating_votes != payload.vote_count:
        movie.rating_votes = payload.vote_count
        changed = True

    movie.tmdb_metadata_fetched_at = datetime.now(UTC)

    return changed
