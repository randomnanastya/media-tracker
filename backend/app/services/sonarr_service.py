from datetime import datetime

from sqlalchemy import select

from app.client.sonarr_client import fetch_sonarr_episodes, fetch_sonarr_series
from app.core.logging import logger
from app.models import Episode, Media, MediaType, Season, Series
from app.schemas.error_codes import SonarrErrorCode
from app.schemas.sonarr import ErrorDetail, SonarrImportResponse


async def import_sonarr_series(session) -> SonarrImportResponse:
    logger.info("Starting Sonarr series import...")

    try:
        sonarr_series = await fetch_sonarr_series()
    except Exception as e:
        logger.error("Failed to fetch series from Sonarr: %s", str(e))
        return SonarrImportResponse(
            error=ErrorDetail(
                code=SonarrErrorCode.SONARR_FETCH_FAILED,
                message=f"Failed to fetch series: {e!s}",
            )
        )

    total_new_series = 0
    total_updated_series = 0
    total_new_episodes = 0
    total_updated_episodes = 0

    for s in sonarr_series:
        sonarr_id = s.get("id")
        imdb_id = s.get("imdbId")
        title = s.get("title")
        if not title:
            logger.warning("Skipping series with missing title: %s", s)
            continue

        release_date_str = s.get("firstAired")
        try:
            release_date = datetime.fromisoformat(release_date_str) if release_date_str else None
        except ValueError:
            logger.error("Invalid firstAired date for series %s: %s", title, release_date_str)
            release_date = None

        year = s.get("year")

        # Check for existing series: Prioritize imdb_id, fallback to title + year
        series = None
        if imdb_id:
            series = await session.scalar(select(Series).where(Series.imdb_id == imdb_id))
        if not series:
            series = await session.scalar(
                select(Series).join(Media).where(Media.title == title, Series.year == year)
            )

        if series:
            # Existing series: Update sonarr_id if changed, imdb_id if missing
            updated = False
            if series.sonarr_id != sonarr_id:
                series.sonarr_id = sonarr_id
                updated = True
            if series.imdb_id is None and imdb_id:
                series.imdb_id = imdb_id
                updated = True

            # Supplement metadata if missing
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
                series.year = year
                updated = True
            if series.genres is None:
                series.genres = s.get("genres")
                updated = True

            # Always update ratings and status
            new_rating_value = s.get("ratings", {}).get("value")
            if series.rating_value != new_rating_value:
                series.rating_value = new_rating_value
                updated = True
            new_rating_votes = s.get("ratings", {}).get("votes")
            if series.rating_votes != new_rating_votes:
                series.rating_votes = new_rating_votes
                updated = True
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
            # New series: Create media first
            # Check for existing media by title (fallback, but should be rare if series check failed)
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

            # Create series
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
                year=year,
                genres=s.get("genres"),
                rating_value=s.get("ratings", {}).get("value"),
                rating_votes=s.get("ratings", {}).get("votes"),
            )
            session.add(series)
            await session.flush()
            total_new_series += 1
            logger.info(
                "Created new series '%s' (sonarr_id: %d, imdb_id: %s)", title, sonarr_id, imdb_id
            )

        # --- Seasons & Episodes ---
        episodes_data = await fetch_sonarr_episodes(sonarr_id)
        new_episodes_count = 0
        updated_episodes_count = 0

        for ep in episodes_data:
            season_number = ep.get("seasonNumber")
            episode_number = ep.get("episodeNumber")
            ep_title = ep.get("title")
            if not ep_title:
                logger.warning("Skipping episode with missing title in series '%s': %s", title, ep)
                continue

            # Create season if not exists (no update, as no new data)
            season = await session.scalar(
                select(Season).where(Season.series_id == series.id, Season.number == season_number)
            )
            if not season:
                season = Season(series_id=series.id, number=season_number)
                session.add(season)
                await session.flush()
                logger.debug("Created new season %d for series '%s'", season_number, title)

            # Episode: Create or update
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
                # Update if changed
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
                # New episode
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
                logger.info("Updated %d episodes for series '%s'", updated_episodes_count, title)
        else:
            logger.info(
                "No changes to episodes for series '%s' (total in Sonarr: %d)",
                title,
                len(episodes_data),
            )

        total_new_episodes += new_episodes_count
        total_updated_episodes += updated_episodes_count

    await session.commit()
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
