import asyncio
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

import httpx
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.client.tmdb_bridge_client import TmdbBridgeClientError, fetch_tmdb_series
from app.config import logger
from app.models import Episode, Season, Series
from app.schemas.tmdb_bridge import (
    TmdbBridgeEpisodeResponse,
    TmdbBridgeSeasonResponse,
    TmdbBridgeSeriesResponse,
    TmdbMetadataUpdateResponse,
)
from app.services.series_utils import map_tmdb_series_status

CONCURRENCY_LIMIT = 10


@dataclass
class _Counters:
    processed: int = field(default=0)
    updated: int = field(default=0)
    skipped: int = field(default=0)
    failed: int = field(default=0)


async def update_series_tmdb_metadata(session: AsyncSession) -> TmdbMetadataUpdateResponse:
    """Fetch TMDB metadata for all series with tmdb_id, update Series/Season/Episode."""
    query = (
        select(Series)
        .where(Series.tmdb_id.is_not(None))
        .options(
            selectinload(Series.media),
            selectinload(Series.seasons).selectinload(Season.episodes),
        )
    )
    series_list = list((await session.execute(query)).scalars().all())

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    counters = _Counters()

    # Phase 1: fetch from TMDB concurrently
    async with httpx.AsyncClient() as http_client:
        fetch_results = await asyncio.gather(
            *[_fetch_one_series(s, semaphore, counters, http_client) for s in series_list],
            return_exceptions=True,
        )

    # Phase 2: apply DB writes sequentially (session is not concurrency-safe)
    for result in fetch_results:
        if isinstance(result, BaseException):
            logger.error("Unexpected error processing series: %s", result)
            counters.failed += 1
            continue
        if result is None:
            continue
        series, payload = result
        try:
            changed = await _apply_tmdb_series_update(series, payload, session)
            if changed:
                counters.updated += 1
        except Exception as e:
            logger.error("Unexpected error processing series: %s", e)
            counters.failed += 1

    try:
        await session.commit()
    except Exception as e:
        logger.error("TMDB series metadata commit failed: %s", e)
        await session.rollback()
        raise

    logger.info(
        "TMDB series metadata update done: processed=%d, updated=%d, skipped=%d, failed=%d",
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


async def _fetch_one_series(
    series: Series,
    semaphore: asyncio.Semaphore,
    counters: _Counters,
    client: httpx.AsyncClient,
) -> tuple[Series, TmdbBridgeSeriesResponse] | None:
    """Fetch + validate TMDB data for one series. Returns (series, payload) or None."""
    async with semaphore:
        tmdb_id = series.tmdb_id
        assert tmdb_id is not None  # guaranteed by WHERE tmdb_id IS NOT NULL
        counters.processed += 1

        try:
            raw = await fetch_tmdb_series(tmdb_id, client=client)
        except TmdbBridgeClientError as e:
            logger.error("Skip tmdb_id=%s due to Bridge error: %s", tmdb_id, e.message)
            counters.failed += 1
            return None

        if raw is None:
            counters.skipped += 1
            return None

        try:
            payload = TmdbBridgeSeriesResponse.model_validate(raw)
        except ValidationError as e:
            logger.error("Bridge payload validation failed for series tmdb_id=%s: %s", tmdb_id, e)
            counters.failed += 1
            return None

        return series, payload


async def _apply_tmdb_series_update(
    series: Series,
    payload: TmdbBridgeSeriesResponse,
    session: AsyncSession,
) -> bool:
    """Apply field-level updates to series, then process seasons + episodes."""
    changed = _apply_series_fields(series, payload)
    changed |= await _process_seasons(series, payload.seasons, session)
    series.tmdb_metadata_fetched_at = datetime.now(UTC)
    return changed


def _apply_series_fields(series: Series, payload: TmdbBridgeSeriesResponse) -> bool:
    """Series-level field updates (without seasons/episodes)."""
    changed = False

    # title: overwrite (TMDB is authoritative for display title)
    if payload.name and series.media and series.media.title != payload.name:
        series.media.title = payload.name
        changed = True

    # status: overwrite
    mapped_status = map_tmdb_series_status(payload.status)
    if mapped_status is not None and series.status != mapped_status:
        series.status = mapped_status
        changed = True

    # first_air_date: overwrite
    new_first_air_date = _to_datetime(payload.first_air_date)
    if new_first_air_date is not None and series.first_air_date != new_first_air_date:
        series.first_air_date = new_first_air_date
        changed = True

    # last_air_date: overwrite
    new_last_air_date = _to_datetime(payload.last_air_date)
    if new_last_air_date is not None and series.last_air_date != new_last_air_date:
        series.last_air_date = new_last_air_date
        changed = True

    # number_of_seasons: overwrite
    if (
        payload.number_of_seasons is not None
        and series.number_of_seasons != payload.number_of_seasons
    ):
        series.number_of_seasons = payload.number_of_seasons
        changed = True

    # number_of_episodes: overwrite
    if (
        payload.number_of_episodes is not None
        and series.number_of_episodes != payload.number_of_episodes
    ):
        series.number_of_episodes = payload.number_of_episodes
        changed = True

    # rating_value: overwrite
    if payload.vote_average is not None and series.rating_value != payload.vote_average:
        series.rating_value = payload.vote_average
        changed = True

    # original_name: fill-if-empty
    if payload.original_name and not series.original_name:
        series.original_name = payload.original_name
        changed = True

    # overview: fill-if-empty
    if payload.overview and not series.overview:
        series.overview = payload.overview
        changed = True

    # backdrop_path: fill-if-empty
    if payload.backdrop_path and not series.backdrop_path:
        series.backdrop_path = payload.backdrop_path
        changed = True

    # poster_url: fill-if-empty
    if payload.poster_url and not series.poster_url:
        series.poster_url = payload.poster_url
        changed = True

    # genres: fill-if-empty
    if not series.genres and payload.genres:
        series.genres = [g.name for g in payload.genres]
        changed = True

    return changed


async def _process_seasons(
    series: Series,
    payload_seasons: list[TmdbBridgeSeasonResponse],
    session: AsyncSession,
) -> bool:
    """Match by series_id + season_number, create new if missing."""
    existing_by_num = {s.number: s for s in series.seasons}
    changed = False

    for season_payload in payload_seasons:
        season = existing_by_num.get(season_payload.season_number)
        if season is None:
            season = Season(
                series_id=series.id,
                number=season_payload.season_number,
            )
            season.episodes = []
            session.add(season)
            await session.flush()
            existing_by_num[season_payload.season_number] = season
            changed = True

        # tmdb_id: fill-if-empty with savepoint to catch unique constraint violation
        if season_payload.tmdb_id is not None and season.tmdb_id is None:
            try:
                sp = await session.begin_nested()
                season.tmdb_id = season_payload.tmdb_id
                await session.flush()
                await sp.commit()
                changed = True
            except IntegrityError:
                await sp.rollback()
                logger.warning(
                    "Duplicate season tmdb_id=%d for season %s, skipping",
                    season_payload.tmdb_id,
                    season.id,
                )

        changed |= _apply_season_fields(season, season_payload)
        changed |= _process_episodes(season, season_payload.episodes)

    return changed


def _apply_season_fields(season: Season, payload: TmdbBridgeSeasonResponse) -> bool:
    """overview/poster_url — fill-if-empty; release_date/vote_average — overwrite."""
    changed = False

    # overview: fill-if-empty
    if payload.overview and not season.overview:
        season.overview = payload.overview
        changed = True

    # poster_url: fill-if-empty
    if payload.poster_url and not season.poster_url:
        season.poster_url = payload.poster_url
        changed = True

    # release_date: overwrite (from air_date)
    new_release_date = _to_datetime(payload.air_date)
    if new_release_date is not None and season.release_date != new_release_date:
        season.release_date = new_release_date
        changed = True

    # vote_average: overwrite
    if payload.vote_average is not None and season.vote_average != payload.vote_average:
        season.vote_average = payload.vote_average
        changed = True

    return changed


def _process_episodes(
    season: Season,
    payload_episodes: list[TmdbBridgeEpisodeResponse],
) -> bool:
    """Match by season_id + episode_number, create new if missing."""
    existing_by_num = {ep.number: ep for ep in season.episodes}
    changed = False

    for ep_payload in payload_episodes:
        ep = existing_by_num.get(ep_payload.episode_number)
        if ep is None:
            ep = Episode(
                season_id=season.id,
                number=ep_payload.episode_number,
                title=ep_payload.name or f"Episode {ep_payload.episode_number}",
                tmdb_id=ep_payload.tmdb_episode_id,
                episode_type=ep_payload.episode_type,
                still_url=ep_payload.still_url,
                overview=ep_payload.overview,
                air_date=_to_datetime(ep_payload.air_date),
                vote_average=(
                    ep_payload.vote_average if (ep_payload.vote_average or 0) > 0 else None
                ),
            )
            season.episodes.append(ep)
            changed = True
        else:
            changed |= _apply_episode_fields(ep, ep_payload)

    return changed


def _apply_episode_fields(ep: Episode, payload: TmdbBridgeEpisodeResponse) -> bool:
    """Episode field updates."""
    changed = False

    # tmdb_id: fill-if-empty
    if payload.tmdb_episode_id is not None and ep.tmdb_id is None:
        ep.tmdb_id = payload.tmdb_episode_id
        changed = True

    # title: fill-if-empty
    if payload.name and not ep.title:
        ep.title = payload.name
        changed = True

    # overview: fill-if-empty
    if payload.overview and not ep.overview:
        ep.overview = payload.overview
        changed = True

    # episode_type: fill-if-empty
    if payload.episode_type and not ep.episode_type:
        ep.episode_type = payload.episode_type
        changed = True

    # still_url: fill-if-empty
    if payload.still_url and not ep.still_url:
        ep.still_url = payload.still_url
        changed = True

    # air_date: overwrite
    new_air_date = _to_datetime(payload.air_date)
    if new_air_date is not None and ep.air_date != new_air_date:
        ep.air_date = new_air_date
        changed = True

    # vote_average: overwrite only if > 0
    if (payload.vote_average or 0) > 0 and ep.vote_average != payload.vote_average:
        ep.vote_average = payload.vote_average
        changed = True

    return changed


def _to_datetime(d: date | None) -> datetime | None:
    if d is None:
        return None
    return datetime.combine(d, datetime.min.time()).replace(tzinfo=UTC)
