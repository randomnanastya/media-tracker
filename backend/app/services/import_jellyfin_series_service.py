from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.client.jellyfin_client import (
    fetch_jellyfin_episodes,
    fetch_jellyfin_series,
)
from app.models import Episode, Media, MediaType, Season, Series
from app.schemas.jellyfin import JellyfinImportSeriesResponse
from app.services.series_utils import find_series_by_external_ids

logger = logging.getLogger(__name__)


async def _find_series_by_jellyfin_id(session: AsyncSession, jellyfin_id: str) -> Series | None:
    """Find series by Jellyfin ID."""
    query = (
        select(Series).where(Series.jellyfin_id == jellyfin_id).options(selectinload(Series.media))
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


def _parse_iso_utc(dt_str: str | None) -> datetime | None:
    """Parse ISO date string to UTC datetime."""
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)
    except (ValueError, TypeError) as exc:
        logger.warning("Invalid ISO date %s: %s", dt_str, exc)
        return None


def _update_existing_series(
    series: Series,
    jellyfin_id: str,
    tvdb_id: str | None,
    imdb_id: str | None,
    tmdb_id: str | None,
    release_date: datetime | None,
    title: str,
    status: str | None,
    year: int | None,
) -> bool:
    """Update series only if field is missing."""
    was_updated = False

    # Always set jellyfin_id if not set
    if series.jellyfin_id is None:
        series.jellyfin_id = jellyfin_id
        was_updated = True

    if tvdb_id and series.tvdb_id is None:
        series.tvdb_id = tvdb_id
        was_updated = True

    if imdb_id and series.imdb_id is None:
        series.imdb_id = imdb_id
        was_updated = True

    if tmdb_id and series.tmdb_id is None:
        series.tmdb_id = tmdb_id
        was_updated = True

    if title and series.media.title != title:
        series.media.title = title
        was_updated = True

    if status and series.status is None:
        series.status = status
        was_updated = True

    if year is not None and series.year is None:
        series.year = year
        was_updated = True

    if release_date and series.media.release_date is None:
        series.media.release_date = release_date
        was_updated = True

    if was_updated:
        logger.info("Updated series '%s' (jellyfin_id=%s)", title, jellyfin_id)

    return was_updated


async def _create_new_series(
    session: AsyncSession,
    title: str,
    jellyfin_id: str,
    tvdb_id: str | None,
    imdb_id: str | None,
    tmdb_id: str | None,
    release_date: datetime | None,
    status: str | None,
    year: int | None,
) -> Series:
    """Create new series with Media."""
    media = Media(
        media_type=MediaType.SERIES,
        title=title,
        release_date=release_date,
    )
    session.add(media)
    await session.flush()

    series = Series(
        id=media.id,
        jellyfin_id=jellyfin_id,
        tvdb_id=tvdb_id,
        imdb_id=imdb_id,
        tmdb_id=tmdb_id,
        status=status,
        year=year,
    )
    session.add(series)
    media.series = series
    await session.flush()

    ids = [f"jellyfin_id={jellyfin_id}"]
    if tvdb_id:
        ids.append(f"tvdb={tvdb_id}")
    if imdb_id:
        ids.append(f"imdb={imdb_id}")
    if tmdb_id:
        ids.append(f"tmdb={tmdb_id}")

    logger.info("Created new series: %s (%s)", title, ", ".join(ids))
    return series


async def _process_seasons_and_episodes(
    session: AsyncSession,
    series: Series,
    jellyfin_series_id: str,
) -> tuple[int, int]:
    """Process seasons and episodes from Jellyfin episodes."""
    episodes_raw = await fetch_jellyfin_episodes(jellyfin_series_id)
    if not episodes_raw:
        return 0, 0

    # Load existing seasons
    existing_seasons_result = await session.scalars(
        select(Season).where(Season.series_id == series.id)
    )
    existing_seasons: dict[tuple[int, str | None], Season] = {
        (s.number, s.jellyfin_id): s for s in existing_seasons_result
    }

    # Load existing episodes by jellyfin_id
    existing_eps_result = await session.scalars(
        select(Episode).where(Episode.season_id.in_([s.id for s in existing_seasons.values()]))
    )
    existing_eps: dict[str, Episode] = {
        str(ep.jellyfin_id): ep for ep in existing_eps_result if ep.jellyfin_id is not None
    }

    new_ep_cnt = upd_ep_cnt = 0
    season_first_air: dict[int, datetime] = {}

    for ep_raw in episodes_raw:
        ep_jellyfin_id = ep_raw.get("Id")
        season_num = ep_raw.get("ParentIndexNumber")
        ep_num = ep_raw.get("IndexNumber")
        ep_title = ep_raw.get("Name")
        air_str = ep_raw.get("PremiereDate")
        season_jellyfin_id = ep_raw.get("SeasonId")

        if not all(
            [ep_jellyfin_id, isinstance(season_num, int), isinstance(ep_num, int), ep_title]
        ):
            continue

        air_date = _parse_iso_utc(air_str)
        if air_date and (
            season_num not in season_first_air or air_date < season_first_air[season_num]
        ):
            season_first_air[season_num] = air_date

        # Get or create season
        season_key = (season_num, season_jellyfin_id)
        season = existing_seasons.get(season_key)
        if not season:
            season = Season(
                series_id=series.id,
                number=season_num,
                jellyfin_id=season_jellyfin_id,  # ← str, не int!
            )
            session.add(season)
            await session.flush()
            existing_seasons[season_key] = season

        # Update season release_date if missing
        if season.release_date is None and season_num in season_first_air:
            season.release_date = season_first_air[season_num]

        # Update or create episode
        existing = existing_eps.get(ep_jellyfin_id)
        if existing:
            updated = False
            if existing.number != ep_num:
                existing.number = ep_num
                updated = True
            if existing.title != ep_title:
                existing.title = ep_title
                updated = True
            if existing.air_date != air_date:
                existing.air_date = air_date
                updated = True
            if updated:
                upd_ep_cnt += 1
        else:
            episode = Episode(
                season_id=season.id,
                jellyfin_id=ep_jellyfin_id,  # ← str, не int!
                number=ep_num,
                title=ep_title,
                air_date=air_date,
            )
            session.add(episode)
            new_ep_cnt += 1
            existing_eps[ep_jellyfin_id] = episode

    if new_ep_cnt or upd_ep_cnt:
        await session.flush()
        logger.info(
            "Series '%s': +%d episodes, ±%d updates",
            series.media.title,
            new_ep_cnt,
            upd_ep_cnt,
        )

    return new_ep_cnt, upd_ep_cnt


async def import_jellyfin_series(session: AsyncSession) -> JellyfinImportSeriesResponse:
    """Import series from Jellyfin: add missing data, link by jellyfin_id."""
    logger.info("Starting Jellyfin series import...")
    jellyfin_series = await fetch_jellyfin_series()

    total_new_series = total_updated_series = 0
    total_new_episodes = total_updated_episodes = 0

    try:
        for raw in jellyfin_series:
            jellyfin_id = raw.get("Id")
            title = raw.get("Name")

            logger.debug("Processing Jellyfin series: ID=%s, Title=%s", jellyfin_id, title)

            if jellyfin_id is not None:
                jellyfin_id = str(jellyfin_id).strip()
                if not jellyfin_id or jellyfin_id == "0":
                    jellyfin_id = None
                elif len(jellyfin_id) > 64:  # Защита от слишком длинных ID
                    logger.warning("Jellyfin ID too long for series '%s': %s", title, jellyfin_id)
                    continue

            if not jellyfin_id or not title:
                logger.warning("Skipping series - missing Id or Name")
                continue

            provider_ids = raw.get("ProviderIds", {})
            tvdb_id = provider_ids.get("Tvdb")
            imdb_id = provider_ids.get("Imdb")
            tmdb_id = provider_ids.get("Tmdb")
            release_date = _parse_iso_utc(raw.get("PremiereDate"))
            status = raw.get("Status")
            year = raw.get("ProductionYear")

            existing_series = None

            # 1. Search by jellyfin_id
            if jellyfin_id:
                existing_series = await _find_series_by_jellyfin_id(session, jellyfin_id)

            # 2. Search by external IDs
            if not existing_series:
                existing_series = await find_series_by_external_ids(
                    session, tmdb_id, imdb_id, tvdb_id
                )

            # 3. Update existing
            if existing_series:
                if _update_existing_series(
                    existing_series,
                    jellyfin_id,
                    tvdb_id,
                    imdb_id,
                    tmdb_id,
                    release_date,
                    title,
                    status,
                    year,
                ):
                    total_updated_series += 1

                new_eps, upd_eps = await _process_seasons_and_episodes(
                    session, existing_series, jellyfin_id
                )
                total_new_episodes += new_eps
                total_updated_episodes += upd_eps
                continue

            # 4. Skip if no identifiers
            if not (jellyfin_id or tvdb_id or imdb_id or tmdb_id):
                logger.warning("Skipping series '%s' - no identifiers", title)
                continue

            # 5. Create new
            new_series = await _create_new_series(
                session,
                title,
                jellyfin_id,
                tvdb_id,
                imdb_id,
                tmdb_id,
                release_date,
                status,
                year,
            )
            total_new_series += 1

            new_eps, upd_eps = await _process_seasons_and_episodes(session, new_series, jellyfin_id)
            total_new_episodes += new_eps
            total_updated_episodes += upd_eps

        await session.commit()
        logger.info(
            "Jellyfin import completed: %d new, %d updated, %d new episodes, %d updated",
            total_new_series,
            total_updated_series,
            total_new_episodes,
            total_updated_episodes,
        )

        return JellyfinImportSeriesResponse(
            new_series=total_new_series,
            updated_series=total_updated_series,
            new_episodes=total_new_episodes,
            updated_episodes=total_updated_episodes,
        )

    except Exception as e:
        logger.error("Jellyfin import failed: %s", e)
        await session.rollback()
        raise
