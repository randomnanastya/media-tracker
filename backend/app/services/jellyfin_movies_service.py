from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.jellyfin_client import fetch_jellyfin_movies_for_user
from app.config import logger
from app.models import Media, MediaType, Movie, User
from app.schemas.jellyfin import JellyfinMoviesSyncResponse


def _parse_jellyfin_date(date_str: str | None) -> datetime | None:
    """Safely parse Jellyfin ISO date (with Z or timezone)."""
    if not date_str or not isinstance(date_str, str):
        return None

    try:
        iso_str = date_str.strip()
        if iso_str.endswith("Z"):
            iso_str = iso_str[:-1] + "+00:00"

        dt = datetime.fromisoformat(iso_str)
        dt = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
        return dt
    except Exception as e:
        logger.debug("Failed to parse Jellyfin date '%s': %s", date_str, e)
        return None


async def sync_jellyfin_movies(session: AsyncSession) -> JellyfinMoviesSyncResponse:
    """Sync watched status for all users from Jellyfin."""
    result = await session.execute(select(User))
    users = result.scalars().all()
    if not users:
        logger.info("No users in DB to sync Jellyfin watched movies")
        return JellyfinMoviesSyncResponse(
            status="success",
            synced_count=0,
            updated_count=0,
            added_count=0,
        )

    total_synced = 0
    total_updated = 0
    total_added = 0

    for user in users:
        if not user.jellyfin_user_id:
            logger.debug("User %s has no jellyfin_user_id, skipping", user.username)
            continue

        movies = await fetch_jellyfin_movies_for_user(user.jellyfin_user_id)
        synced, updated, added = await _process_user_movies(session, user.id, movies)
        total_synced += synced
        total_updated += updated
        total_added += added

    try:
        await session.commit()
    except Exception as e:
        logger.error("Failed to commit session: %s", e)
        await session.rollback()
        raise

    logger.info(
        "Jellyfin movie sync completed: %d synced, %d updated, %d added",
        total_synced,
        total_updated,
        total_added,
    )
    return JellyfinMoviesSyncResponse(
        status="success",
        synced_count=total_synced,
        updated_count=total_updated,
        added_count=total_added,
    )


async def _process_user_movies(
    session: AsyncSession, user_db_id: int, movies: list[dict[str, Any]]
) -> tuple[int, int, int]:
    """Process movies for one user: match, update, add new."""
    synced = 0
    updated = 0
    added = 0

    for m in movies:
        jellyfin_id = m.get("Id")
        title = m.get("Name", "Unknown Movie")
        provider_ids = m.get("ProviderIds", {})
        tmdb_id = provider_ids.get("Tmdb")
        imdb_id = provider_ids.get("Imdb")

        user_data = m.get("UserData", {})
        played = bool(user_data.get("Played", False))
        last_played = user_data.get("LastPlayedDate")

        watched_at = None
        if played and last_played:
            try:
                watched_at = datetime.fromisoformat(last_played.replace("Z", "+00:00"))
                watched_at = watched_at.astimezone(UTC)
            except Exception as e:
                logger.warning("Failed to parse LastPlayedDate for %s: %s", title, e)

        # Переписанная логика поиска фильма
        movie_obj = None

        # Сначала ищем по tmdb_id
        if tmdb_id:
            query = (
                select(Movie)
                .join(Media)
                .where(Media.media_type == MediaType.MOVIE, Movie.tmdb_id == tmdb_id)
            )
            result = await session.execute(query)
            movie_obj = result.scalars().first()

        # Если не нашли по tmdb_id, ищем по imdb_id
        if not movie_obj and imdb_id:
            query = (
                select(Movie)
                .join(Media)
                .where(Media.media_type == MediaType.MOVIE, Movie.imdb_id == imdb_id)
            )
            result = await session.execute(query)
            movie_obj = result.scalars().first()

        if movie_obj:
            needs_update = False
            if movie_obj.jellyfin_id != jellyfin_id:
                movie_obj.jellyfin_id = jellyfin_id
                needs_update = True
            if movie_obj.watched != played:
                movie_obj.watched = played
                movie_obj.watched_at = watched_at
                needs_update = True
            if needs_update:
                session.add(movie_obj)
                updated += 1
                logger.debug("Updated movie: %s (watched=%s)", title, played)
        else:
            premiere_date_str = m.get("PremiereDate")
            release_date = _parse_jellyfin_date(premiere_date_str)
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
                    radarr_id=None,
                    tmdb_id=tmdb_id,
                    imdb_id=imdb_id,
                    jellyfin_id=jellyfin_id,
                    watched=played,
                    watched_at=watched_at,
                )
                session.add(movie_obj)
                await session.flush()
                added += 1
                logger.info(
                    "Added new movie from Jellyfin: %s (release: %s)",
                    title,
                    release_date.isoformat() if release_date else "unknown",
                )
            except Exception as e:
                logger.error("Failed to add movie from Jellyfin: %s | %s", title, e)
                await session.rollback()
                continue

        synced += 1

    return synced, updated, added
