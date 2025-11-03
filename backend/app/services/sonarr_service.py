from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.sonarr_client import fetch_sonarr_episodes, fetch_sonarr_series
from app.config import logger
from app.exceptions.client_errors import ClientError
from app.models import Episode, Media, MediaType, Season, Series
from app.schemas.error_codes import SonarrErrorCode
from app.schemas.responses import ErrorDetail
from app.schemas.sonarr import SonarrImportResponse


async def import_sonarr_series(session: AsyncSession) -> SonarrImportResponse:
    logger.info("Starting Sonarr series import...")
    sonarr_series = await fetch_sonarr_series()

    total_new_series = 0
    total_updated_series = 0
    total_new_episodes = 0
    total_updated_episodes = 0
    try:

        for s in sonarr_series:
            sonarr_id = s.get("id")

            if not isinstance(sonarr_id, int):
                logger.warning(
                    "Skipping series '%s' with invalid sonarr_id type: %s (value: %s)",
                    s.get("title"),
                    type(sonarr_id),
                    sonarr_id,
                )
                continue

            imdb_id = s.get("imdbId")
            title = s.get("title")
            if not title:
                logger.warning("Skipping series with missing title: %s", s)
                continue

            release_date_str = s.get("firstAired")
            try:
                release_date = (
                    datetime.fromisoformat(release_date_str) if release_date_str else None
                )
            except ValueError:
                logger.error("Invalid firstAired date for series %s: %s", title, release_date_str)
                release_date = None

            year = s.get("year")

            series = None

            if imdb_id:
                series = await session.scalar(select(Series).where(Series.imdb_id == imdb_id))
            if not series:
                series = await session.scalar(
                    select(Series).join(Media).where(Media.title == title, Series.year == year)
                )

            if series:
                updated = False
                if series.sonarr_id != sonarr_id:
                    series.sonarr_id = sonarr_id
                    updated = True
                if series.imdb_id is None and imdb_id:
                    series.imdb_id = imdb_id
                    updated = True

                poster = next(
                    (
                        img.get("remoteUrl")
                        for img in s.get("images", [])
                        if img.get("coverType") == "poster"
                    ),
                    None,
                )

                if series.poster_url is None and poster:
                    series.poster_url = poster
                    updated = True

                if series.year is None and year:
                    try:
                        series.year = int(year)
                        updated = True
                    except ValueError:
                        logger.warning("Invalid year is not int for series %s: %s", title, year)

                if series.genres is None:
                    series.genres = s.get("genres")
                    updated = True

                new_rating_value = s.get("ratings", {}).get("value")
                if series.rating_value != new_rating_value:
                    series.rating_value = new_rating_value
                    updated = True

                new_rating_votes = s.get("ratings", {}).get("votes")
                if series.rating_votes != new_rating_votes:
                    try:
                        series.rating_votes = int(new_rating_votes)
                        updated = True
                    except ValueError:
                        logger.warning(
                            "Invalid rating votes is not int for series %s: %s",
                            title,
                            new_rating_votes,
                        )

                new_status = s.get("status")
                if series.status != new_status:
                    series.status = new_status
                    updated = True

                if updated:
                    await session.flush()
                    total_updated_series += 1
                    logger.info(
                        "Updated existing series '%s' (sonarr_id: %d, imdb_id: %s)",
                        title,
                        sonarr_id,
                        imdb_id,
                    )

            else:
                media = await session.scalar(
                    select(Media).where(Media.title == title, Media.media_type == MediaType.SERIES)
                )
                if not media:
                    media = Media(
                        media_type=MediaType.SERIES,
                        title=title,
                        release_date=release_date,
                    )
                    session.add(media)
                    await session.flush()

                poster = next(
                    (
                        img.get("remoteUrl")
                        for img in s.get("images", [])
                        if img.get("coverType") == "poster"
                    ),
                    None,
                )
                series = Series(
                    id=media.id,
                    sonarr_id=sonarr_id,
                    imdb_id=imdb_id,
                    status=s.get("status"),
                    poster_url=poster,
                    year=int(year) if year is not None else None,
                    genres=s.get("genres"),
                    rating_value=s.get("ratings", {}).get("value"),
                    rating_votes=(
                        int(s.get("ratings", {}).get("votes"))
                        if s.get("ratings", {}).get("votes") is not None
                        else None
                    ),
                )
                session.add(series)
                await session.flush()
                total_new_series += 1
                logger.info(
                    "Created new series '%s' (sonarr_id: %d, imdb_id: %s)",
                    title,
                    sonarr_id,
                    imdb_id,
                )

            episodes_data = await fetch_sonarr_episodes(sonarr_id)
            new_episodes_count = 0
            updated_episodes_count = 0

            for ep in episodes_data:
                season_number = ep.get("seasonNumber")
                episode_number = ep.get("episodeNumber")
                ep_title = ep.get("title")
                if not ep_title:
                    logger.warning(
                        "Skipping episode with missing title in series '%s': %s", title, ep
                    )
                    continue

                season = await session.scalar(
                    select(Season).where(
                        Season.series_id == series.id, Season.number == season_number
                    )
                )
                if not season:
                    season = Season(series_id=series.id, number=season_number)
                    session.add(season)
                    await session.flush()
                    logger.debug("Created new season %d for series '%s'", season_number, title)

                ep_sonarr_id = ep["id"]
                existing_ep = await session.scalar(
                    select(Episode).where(Episode.sonarr_id == ep_sonarr_id)
                )

                air_date_str = ep.get("airDateUtc")
                try:
                    air_date = (
                        datetime.fromisoformat(air_date_str.replace("Z", "+00:00"))
                        if air_date_str
                        else None
                    )
                except ValueError:
                    logger.error(
                        "Invalid airDateUtc for episode '%s' in series '%s': %s",
                        ep_title,
                        title,
                        air_date_str,
                    )
                    air_date = None

                overview = ep.get("overview")

                if existing_ep:
                    updated_ep = False
                    if existing_ep.number != episode_number:
                        existing_ep.number = episode_number
                        updated_ep = True
                    if existing_ep.title != ep_title:
                        existing_ep.title = ep_title
                        updated_ep = True
                    if existing_ep.overview != overview:
                        existing_ep.overview = overview
                        updated_ep = True
                    if existing_ep.air_date != air_date:
                        existing_ep.air_date = air_date
                        updated_ep = True
                    if updated_ep:
                        updated_episodes_count += 1
                else:
                    episode = Episode(
                        season_id=season.id,
                        sonarr_id=ep_sonarr_id,
                        number=episode_number,
                        title=ep_title,
                        overview=overview,
                        air_date=air_date,
                    )
                    session.add(episode)
                    new_episodes_count += 1

            if new_episodes_count > 0 or updated_episodes_count > 0:
                await session.flush()
                if new_episodes_count > 0:
                    logger.info("Added %d new episodes for series '%s'", new_episodes_count, title)
                if updated_episodes_count > 0:
                    logger.info(
                        "Updated %d episodes for series '%s'", updated_episodes_count, title
                    )
            else:
                logger.info(
                    "No changes to episodes for series '%s' (total in Sonarr: %d)",
                    title,
                    len(episodes_data),
                )

            total_new_episodes += new_episodes_count
            total_updated_episodes += updated_episodes_count

        try:
            await session.commit()
        except Exception as e:
            logger.error("Failed to commit session: %s", e)
            await session.rollback()
            raise

        logger.info(
            "Sonarr import completed: %d new series, %d updated series, %d new episodes, %d updated episodes",
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

        if e.code in (SonarrErrorCode.INTERNAL_ERROR,):  # конфиг-ошибки
            raise  # ← ПРОБРОСИТЬ
        error_msg = (
            "Sonarr is unreachable. Check connection."
            if e.code == SonarrErrorCode.NETWORK_ERROR
            else (
                "Failed to retrieve series from Sonarr."
                if e.code in (SonarrErrorCode.FETCH_FAILED, SonarrErrorCode.INTERNAL_ERROR)
                else "Sonarr import failed."
            )
        )

        return SonarrImportResponse(
            error=ErrorDetail(code=e.code, message=error_msg),
            new_series=None,
            updated_series=None,
            new_episodes=None,
            updated_episodes=None,
        )

    except SQLAlchemyError as e:
        await session.rollback()
        logger.exception("Database error during Sonarr import: %s", e)
        raise
    except Exception:
        await session.rollback()
        logger.exception("CRITICAL: Unexpected error in Sonarr import")
        raise
