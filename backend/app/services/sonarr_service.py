from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.sonarr_client import fetch_sonarr_episodes, fetch_sonarr_series
from app.exceptions.client_errors import ClientError
from app.models import Episode, Media, MediaType, Season, Series
from app.schemas.error_codes import SonarrErrorCode
from app.schemas.responses import ErrorDetail
from app.schemas.sonarr import SonarrImportResponse

logger = logging.getLogger(__name__)


async def _find_series_by_sonarr_id(session: AsyncSession, sonarr_id: int) -> Series | None:
    result = await session.execute(select(Series).where(Series.sonarr_id == sonarr_id))
    return result.scalar_one_or_none()


async def _find_series_by_external_ids(
    session: AsyncSession,
    tvdb_id: str | None,
    imdb_id: str | None,
) -> Series | None:
    if not tvdb_id and not imdb_id:
        return None

    conditions = []
    if tvdb_id:
        conditions.append(Series.tvdb_id == tvdb_id)
    if imdb_id:
        conditions.append(Series.imdb_id == imdb_id)

    query = select(Series).where(or_(*conditions))
    result = await session.execute(query)
    return result.scalar_one_or_none()


def _parse_iso_utc(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)
    except (ValueError, TypeError) as exc:
        logger.warning("Invalid ISO date %s: %s", dt_str, exc)
        return None


def _extract_poster(images: list[dict[str, Any]]) -> str | None:
    return next(
        (img.get("remoteUrl") for img in images if img.get("coverType") == "poster"),
        None,
    )


def _update_series_if_needed(
    series: Series,
    sonarr_id: int | None,
    tvdb_id: str | None,
    imdb_id: str | None,
    release_date: datetime | None,
    title: str,
    poster_url: str | None,
    year: int | None,
    genres: list[str] | None,
    rating_value: float | None,
    rating_votes: int | None,
    status: str | None,
) -> bool:
    updated = False

    if sonarr_id and series.sonarr_id is None:
        series.sonarr_id = sonarr_id
        updated = True

    if tvdb_id and series.tvdb_id is None:
        series.tvdb_id = tvdb_id
        updated = True

    if imdb_id and series.imdb_id is None:
        series.imdb_id = imdb_id
        updated = True

    if title and series.media.title != title:
        series.media.title = title
        updated = True

    if poster_url and series.poster_url is None:
        series.poster_url = poster_url
        updated = True

    if year is not None and series.year is None:
        series.year = year
        updated = True

    if genres is not None and series.genres is None:
        series.genres = genres
        updated = True

    if rating_value is not None and series.rating_value != rating_value:
        series.rating_value = rating_value
        updated = True

    if rating_votes is not None and series.rating_votes != rating_votes:
        series.rating_votes = rating_votes
        updated = True

    if status and series.status != status:
        series.status = status
        updated = True

    if release_date and series.media.release_date is None:
        series.media.release_date = release_date
        updated = True

    if updated:
        logger.info("Updated series '%s' (sonarr_id=%s)", title, sonarr_id or "—")
    return updated


async def _create_series(
    session: AsyncSession,
    title: str,
    sonarr_id: int | None,
    tvdb_id: str | None,
    imdb_id: str | None,
    release_date: datetime | None,
    poster_url: str | None,
    year: int | None,
    genres: list[str] | None,
    rating_value: float | None,
    rating_votes: int | None,
    status: str | None,
) -> Series:
    media = Media(
        media_type=MediaType.SERIES,
        title=title,
        release_date=release_date,
    )
    session.add(media)
    await session.flush()

    series = Series(
        id=media.id,
        sonarr_id=sonarr_id,
        tvdb_id=tvdb_id,
        imdb_id=imdb_id,
        poster_url=poster_url,
        year=year,
        genres=genres,
        rating_value=rating_value,
        rating_votes=rating_votes,
        status=status,
    )
    session.add(series)
    await session.flush()

    ids = [f"sonarr_id={sonarr_id}"] if sonarr_id else []
    if tvdb_id:
        ids.append(f"tvdb={tvdb_id}")
    if imdb_id:
        ids.append(f"imdb={imdb_id}")
    logger.info("Created new series: %s (%s)", title, ", ".join(ids))
    return series


async def import_sonarr_series(session: AsyncSession) -> SonarrImportResponse:
    logger.info("Starting Sonarr series import...")
    sonarr_series = await fetch_sonarr_series()

    total_new_series = total_updated_series = 0
    total_new_episodes = total_updated_episodes = 0

    try:
        for raw in sonarr_series:
            sonarr_id = raw.get("id")
            if not isinstance(sonarr_id, int):
                logger.warning("Skip series with invalid sonarr_id: %s", raw.get("title"))
                continue

            title = raw.get("title")
            if not title:
                logger.warning("Skip series without title")
                continue

            tvdb_id = str(raw.get("tvdbId")) if raw.get("tvdbId") is not None else None
            imdb_id = raw.get("imdbId")
            release_date = _parse_iso_utc(raw.get("firstAired"))
            year = raw.get("year")
            status = raw.get("status")
            poster_url = _extract_poster(raw.get("images", []))
            genres = raw.get("genres")
            rating_value = raw.get("ratings", {}).get("value")
            rating_votes_raw = raw.get("ratings", {}).get("votes")
            rating_votes = int(rating_votes_raw) if rating_votes_raw is not None else None

            series: Series | None = None

            # 1. Поиск по sonarr_id
            if sonarr_id:
                series = await _find_series_by_sonarr_id(session, sonarr_id)

            # 2. Поиск по внешним ID
            if not series:
                series = await _find_series_by_external_ids(session, tvdb_id, imdb_id)

            # 3. Обновление
            if series:
                if _update_series_if_needed(
                    series=series,
                    sonarr_id=sonarr_id,
                    tvdb_id=tvdb_id,
                    imdb_id=imdb_id,
                    release_date=release_date,
                    title=title,
                    poster_url=poster_url,
                    year=year,
                    genres=genres,
                    rating_value=rating_value,
                    rating_votes=rating_votes,
                    status=status,
                ):
                    total_updated_series += 1
            else:
                # 4. Создание
                if sonarr_id or tvdb_id or imdb_id:
                    series = await _create_series(
                        session=session,
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
                    )
                    total_new_series += 1
                else:
                    logger.warning("Skip series without identifiers: %s", title)
                    continue

            # === Сезоны и эпизоды ===
            sonarr_season_numbers = {
                s["seasonNumber"]
                for s in raw.get("seasons", [])
                if isinstance(s.get("seasonNumber"), int)
            }

            existing_seasons_result = await session.scalars(
                select(Season).where(Season.series_id == series.id)
            )
            existing_seasons: dict[int, Season] = {}
            for season_obj in existing_seasons_result:
                existing_seasons[season_obj.number] = season_obj

            for num in sonarr_season_numbers:
                if num not in existing_seasons:
                    new_season = Season(series_id=series.id, number=num)
                    session.add(new_season)
                    await session.flush()
                    existing_seasons[num] = new_season

            season_first_air: dict[int, str] = {}
            episodes_raw = []
            if sonarr_id:
                episodes_raw = await fetch_sonarr_episodes(sonarr_id)

            for ep in episodes_raw:
                sn = ep.get("seasonNumber")
                air = ep.get("airDateUtc")
                if (
                    isinstance(sn, int)
                    and air
                    and (sn not in season_first_air or air < season_first_air[sn])
                ):
                    season_first_air[sn] = air

            for sn, first_air_str in season_first_air.items():
                season = existing_seasons.get(sn)
                if season is not None and season.release_date is None:
                    dt = _parse_iso_utc(first_air_str)
                    if dt:
                        season.release_date = dt

            existing_eps_result = await session.scalars(
                select(Episode).where(
                    Episode.season_id.in_([s.id for s in existing_seasons.values()])
                )
            )
            existing_eps: dict[int, Episode] = {}
            for episode in existing_eps_result:
                if episode.sonarr_id is not None:
                    existing_eps[episode.sonarr_id] = episode

            new_ep_cnt = upd_ep_cnt = 0
            for ep_raw in episodes_raw:
                ep_sonarr_id = ep_raw.get("id")
                season_num = ep_raw.get("seasonNumber")
                ep_num = ep_raw.get("episodeNumber")
                ep_title = ep_raw.get("title")
                overview = ep_raw.get("overview")
                air_str = ep_raw.get("airDateUtc")

                if (
                    not isinstance(ep_sonarr_id, int)
                    or not isinstance(season_num, int)
                    or not isinstance(ep_num, int)
                    or not ep_title
                ):
                    continue

                season = existing_seasons.get(season_num)
                if season is None:
                    continue

                air_date = _parse_iso_utc(air_str)

                existing = existing_eps.get(ep_sonarr_id)
                if existing is not None:
                    updated = False
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
                logger.info("Series '%s': +%d episodes, ±%d updates", title, new_ep_cnt, upd_ep_cnt)

            total_new_episodes += new_ep_cnt
            total_updated_episodes += upd_ep_cnt

        await session.commit()
        logger.info(
            "Sonarr import finished - new series: %d, updated series: %d, "
            "new episodes: %d, updated episodes: %d",
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

    except ClientError as e:
        await session.rollback()
        logger.error("Sonarr client error: %s", e.message)
        msg = (
            "Sonarr is unreachable. Check connection."
            if e.code == SonarrErrorCode.NETWORK_ERROR
            else (
                "Failed to retrieve series from Sonarr."
                if e.code in (SonarrErrorCode.FETCH_FAILED, SonarrErrorCode.INTERNAL_ERROR)
                else "Sonarr import failed."
            )
        )
        return SonarrImportResponse(
            error=ErrorDetail(code=e.code, message=msg),
            new_series=None,
            updated_series=None,
            new_episodes=None,
            updated_episodes=None,
        )
    except Exception:
        await session.rollback()
        logger.exception("Unexpected error in Sonarr import")
        raise
