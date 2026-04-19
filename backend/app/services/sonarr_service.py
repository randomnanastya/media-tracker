from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.client.sonarr_client import fetch_sonarr_episodes, fetch_sonarr_series
from app.models import Episode, Season, Series, ServiceType
from app.schemas.sonarr import SonarrImportResponse
from app.services.series_utils import (
    create_new_series,
    find_series_by_external_ids,
    update_existing_series,
)
from app.services.service_config_repository import get_decrypted_config
from app.utils.datetime_utils import parse_iso_datetime
from app.utils.poster_utils import extract_poster

logger = logging.getLogger(__name__)


async def _find_series_by_sonarr_id(session: AsyncSession, sonarr_id: int) -> Series | None:
    """Find series by Sonarr ID."""
    query = select(Series).where(Series.sonarr_id == sonarr_id).options(selectinload(Series.media))
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def _process_seasons_and_episodes(
    session: AsyncSession,
    series: Series,
    raw_series_data: dict[str, Any],
    sonarr_id: int | None,
    sonarr_url: str,
    sonarr_api_key: str,
) -> tuple[int, int]:
    """Process seasons and episodes for a series."""
    if not sonarr_id:
        return 0, 0

    # Extract season numbers from Sonarr data
    sonarr_season_numbers = {
        s["seasonNumber"]
        for s in raw_series_data.get("seasons", [])
        if isinstance(s.get("seasonNumber"), int)
    }

    # Load existing seasons
    existing_seasons_result = await session.scalars(
        select(Season).where(Season.series_id == series.id)
    )
    existing_seasons: dict[int, Season] = {
        season_obj.number: season_obj for season_obj in existing_seasons_result
    }

    # Create missing seasons
    for num in sonarr_season_numbers:
        if num not in existing_seasons:
            new_season = Season(series_id=series.id, number=num)
            session.add(new_season)
            await session.flush()
            existing_seasons[num] = new_season

    # Fetch episodes from Sonarr
    episodes_raw = await fetch_sonarr_episodes(sonarr_url, sonarr_api_key, sonarr_id)

    # Determine earliest air date per season
    season_first_air: dict[int, str] = {}
    for ep in episodes_raw:
        sn = ep.get("seasonNumber")
        air = ep.get("airDateUtc")
        if (
            isinstance(sn, int)
            and air
            and (sn not in season_first_air or air < season_first_air[sn])
        ):
            season_first_air[sn] = air

    # Update season release dates if missing
    for sn, first_air_str in season_first_air.items():
        season = existing_seasons.get(sn)
        if season and season.release_date is None:
            dt = parse_iso_datetime(first_air_str, context=f"Season {sn}")
            if dt:
                season.release_date = dt

    # Load existing episodes by sonarr_id (global search to handle episodes that moved seasons)
    ep_sonarr_ids = [ep.get("id") for ep in episodes_raw if isinstance(ep.get("id"), int)]
    existing_eps: dict[int, Episode] = {}
    if ep_sonarr_ids:
        existing_eps_result = await session.scalars(
            select(Episode).where(Episode.sonarr_id.in_(ep_sonarr_ids))
        )
        existing_eps = {ep.sonarr_id: ep for ep in existing_eps_result if ep.sonarr_id is not None}

    new_ep_cnt = upd_ep_cnt = 0
    for ep_raw in episodes_raw:
        ep_sonarr_id = ep_raw.get("id")
        season_num = ep_raw.get("seasonNumber")
        ep_num = ep_raw.get("episodeNumber")
        ep_title = ep_raw.get("title")
        overview = ep_raw.get("overview")
        air_str = ep_raw.get("airDateUtc")

        # Skip invalid episode data
        if (
            not isinstance(ep_sonarr_id, int)
            or not isinstance(season_num, int)
            or not isinstance(ep_num, int)
            or not ep_title
        ):
            continue

        season = existing_seasons.get(season_num)
        if not season:
            continue

        air_date = parse_iso_datetime(air_str, context=f"Episode {ep_num}")

        # Update or create episode
        existing = existing_eps.get(ep_sonarr_id)
        if existing:
            updated = False
            if existing.season_id != season.id:
                existing.season_id = season.id
                updated = True
            if existing.number != ep_num:
                existing.number = ep_num
                updated = True
            if existing.title != ep_title:
                existing.title = ep_title
                updated = True
            if existing.overview != overview:
                existing.overview = overview
                updated = True
            if existing.air_date != air_date:
                existing.air_date = air_date
                updated = True
            if updated:
                upd_ep_cnt += 1
        else:
            episode = Episode(
                season_id=season.id,
                sonarr_id=ep_sonarr_id,
                number=ep_num,
                title=ep_title,
                air_date=air_date,
                overview=overview,
            )
            session.add(episode)
            new_ep_cnt += 1
            existing_eps[ep_sonarr_id] = episode

    if new_ep_cnt or upd_ep_cnt:
        await session.flush()
        logger.info(
            "Series '%s': +%d episodes, ±%d updates",
            series.media.title,
            new_ep_cnt,
            upd_ep_cnt,
        )

    return new_ep_cnt, upd_ep_cnt


async def import_sonarr_series(session: AsyncSession) -> SonarrImportResponse:
    """Import series from Sonarr into the database."""
    config = await get_decrypted_config(session, ServiceType.SONARR)
    if config is None:
        logger.info("Sonarr is not configured, skipping import")
        return SonarrImportResponse(
            new_series=0,
            updated_series=0,
            new_episodes=0,
            updated_episodes=0,
        )
    url, api_key = config

    logger.info("Starting Sonarr series import...")
    sonarr_series = await fetch_sonarr_series(url, api_key)

    total_new_series = total_updated_series = 0
    total_new_episodes = total_updated_episodes = 0

    try:
        for raw in sonarr_series:
            # Extract core series data
            sonarr_id = raw.get("id")
            tmdb_id = str(raw.get("tmdbId")) if raw.get("tmdbId") else None
            imdb_id = str(raw.get("imdbId")) if raw.get("imdbId") else None
            tvdb_id = str(raw.get("tvdbId")) if raw.get("tvdbId") else None
            title = raw.get("title")

            # Skip series without title
            if not title:
                logger.warning("Skipping series (sonarr_id=%s) - missing title", sonarr_id)
                continue

            release_date = parse_iso_datetime(raw.get("firstAired"), context=title)
            poster_url = extract_poster(raw.get("images", []))
            logger.debug("Series '%s' (sonarr_id=%s): poster_url=%s", title, sonarr_id, poster_url)
            year = raw.get("year")
            genres = raw.get("genres")
            rating_value = raw.get("ratings", {}).get("value")
            rating_votes = raw.get("ratings", {}).get("votes")
            status = raw.get("status")

            existing_series = None

            # 1. Search by sonarr_id
            if sonarr_id:
                existing_series = await _find_series_by_sonarr_id(session, sonarr_id)

            # 2. Search by external IDs
            if not existing_series:
                existing_series = await find_series_by_external_ids(
                    session, tmdb_id, imdb_id, tvdb_id
                )

            # 3. Update existing series
            if existing_series:
                if update_existing_series(
                    series=existing_series,
                    title=title,
                    sonarr_id=sonarr_id,
                    tvdb_id=tvdb_id,
                    imdb_id=imdb_id,
                    release_date=release_date,
                    poster_url=poster_url,
                    year=year,
                    genres=genres,
                    rating_value=rating_value,
                    rating_votes=rating_votes,
                    status=status,
                    source="Sonarr",
                ):
                    total_updated_series += 1

                new_eps, updated_eps = await _process_seasons_and_episodes(
                    session, existing_series, raw, sonarr_id, url, api_key
                )
                total_new_episodes += new_eps
                total_updated_episodes += updated_eps
                continue

            # 4. Skip if no identifiers
            if not (sonarr_id or tvdb_id or imdb_id):
                logger.warning(
                    "Skipping series '%s' (sonarr_id=%s, tvdb_id=%s, imdb_id=%s) - no identifiers",
                    title,
                    sonarr_id,
                    tvdb_id,
                    imdb_id,
                )
                continue

            # 5. Create new series
            new_series = await create_new_series(
                session=session,
                title=title,
                sonarr_id=sonarr_id,
                jellyfin_id=None,
                tvdb_id=tvdb_id,
                tmdb_id=None,
                imdb_id=imdb_id,
                release_date=release_date,
                poster_url=poster_url,
                year=year,
                genres=genres,
                rating_value=rating_value,
                rating_votes=rating_votes,
                status=status,
                source="Sonarr",
            )
            total_new_series += 1

            # Process episodes for new series
            new_eps, updated_eps = await _process_seasons_and_episodes(
                session, new_series, raw, sonarr_id, url, api_key
            )
            total_new_episodes += new_eps
            total_updated_episodes += updated_eps

        await session.commit()
        logger.info(
            "Sonarr import completed: %d new series, %d updated, %d new episodes, %d updated",
            total_new_series,
            total_updated_series,
            total_new_episodes,
            total_updated_episodes,
        )

        return SonarrImportResponse(
            new_series=total_new_series,
            updated_series=total_updated_series,
            new_episodes=total_new_episodes,
            updated_episodes=total_updated_episodes,
        )

    except Exception as e:
        logger.error("Sonarr import failed: %s", e)
        await session.rollback()
        raise
