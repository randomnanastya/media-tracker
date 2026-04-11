from collections import defaultdict
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, WatchStatus
from app.schemas.media import MediaItem, MediaListResponse

STATUS_PRIORITY = {
    WatchStatus.WATCHED: 4,
    WatchStatus.WATCHING: 3,
    WatchStatus.PLANNED: 2,
    WatchStatus.DROPPED: 1,
}


async def get_media_list(
    session: AsyncSession,
    media_type: str | None = None,
    status: str | None = None,
    jellyfin_user_id: str | None = None,
) -> MediaListResponse:
    internal_user_id: int | None = None
    if jellyfin_user_id:
        result = await session.execute(
            select(User.id).where(User.jellyfin_user_id == jellyfin_user_id)
        )
        internal_user_id = result.scalar_one_or_none()
        if internal_user_id is None:
            return MediaListResponse(items=[], total=0)

    query = text(
        """
        SELECT
            m.id,
            m.title,
            m.media_type,
            COALESCE(mov.year, s.year) AS year,
            COALESCE(mov.genres, s.genres) AS genres,
            COALESCE(mov.poster_url, s.poster_url) AS poster_url,
            COALESCE(mov.rating_value, s.rating_value) AS rating,
            movie_wh.status AS movie_status,
            movie_wh.user_id AS movie_wh_user_id,
            ep_stats.total_count,
            ep_stats.watched_count,
            ep_stats.watching_count,
            ep_stats.dropped_count
        FROM media m
        LEFT JOIN movies mov ON mov.id = m.id
        LEFT JOIN series s ON s.id = m.id
        LEFT JOIN watch_history movie_wh
            ON movie_wh.media_id = m.id
            AND movie_wh.episode_id IS NULL
            AND (CAST(:user_id AS INTEGER) IS NULL OR movie_wh.user_id = CAST(:user_id AS INTEGER))
        LEFT JOIN LATERAL (
            SELECT
                COUNT(e.id) AS total_count,
                COUNT(*) FILTER (WHERE wh.status = 'WATCHED') AS watched_count,
                COUNT(*) FILTER (WHERE wh.status = 'WATCHING') AS watching_count,
                COUNT(*) FILTER (WHERE wh.status = 'DROPPED') AS dropped_count
            FROM seasons sea
            JOIN episodes e ON e.season_id = sea.id
            LEFT JOIN watch_history wh
                ON wh.episode_id = e.id
                AND (CAST(:user_id AS INTEGER) IS NULL OR wh.user_id = CAST(:user_id AS INTEGER))
            WHERE sea.series_id = m.id
        ) ep_stats ON m.media_type = 'SERIES'
        WHERE (CAST(:type AS VARCHAR) IS NULL OR m.media_type = CAST(:type AS mediatype))
        ORDER BY m.title
    """
    )

    rows = (
        (
            await session.execute(
                query,
                {
                    "user_id": internal_user_id,
                    "type": media_type.upper() if media_type else None,
                },
            )
        )
        .mappings()
        .all()
    )

    def compute_series_status(watched: int, watching: int, dropped: int, total: int) -> str | None:
        if total == 0:
            return None
        if watched == total:
            return "watched"
        if watched > 0 or watching > 0:
            return "watching"
        if dropped > 0:
            return "dropped"
        return "planned"

    grouped: dict[int, list[Any]] = defaultdict(list)
    for row in rows:
        grouped[row["id"]].append(row)

    items: list[MediaItem] = []
    for media_id, media_rows in grouped.items():
        row = media_rows[0]
        media_type_val = row["media_type"]

        if media_type_val == "SERIES":
            total = row["total_count"] or 0
            watched = sum(r["watched_count"] or 0 for r in media_rows)
            watching = sum(r["watching_count"] or 0 for r in media_rows)
            dropped = sum(r["dropped_count"] or 0 for r in media_rows)
            watch_status = compute_series_status(watched, watching, dropped, total)
        else:
            statuses = [
                r["movie_status"].lower() for r in media_rows if r["movie_status"] is not None
            ]
            if not statuses:
                watch_status = None
            else:
                priority_map = {"watched": 4, "watching": 3, "planned": 2, "dropped": 1}
                best = max(statuses, key=lambda s: priority_map.get(s, 0))
                watch_status = best

        if status and watch_status != status:
            continue

        genres = row["genres"] or []
        items.append(
            MediaItem(
                id=media_id,
                title=row["title"],
                media_type=media_type_val.lower(),
                year=row["year"],
                genres=genres,
                poster_url=row["poster_url"],
                rating=row["rating"],
                watch_status=watch_status,
                total_episodes=row["total_count"] if media_type_val == "SERIES" else None,
                watched_episodes=(
                    (row["watched_count"] or 0) if media_type_val == "SERIES" else None
                ),
            )
        )

    return MediaListResponse(items=items, total=len(items))
