from collections import defaultdict
from typing import Any, Literal, cast

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, WatchStatus
from app.schemas.media import MediaDetailResponse, MediaItem, MediaListResponse, SeasonDetail

STATUS_PRIORITY = {
    WatchStatus.WATCHED: 4,
    WatchStatus.WATCHING: 3,
    WatchStatus.PLANNED: 2,
    WatchStatus.DROPPED: 1,
}


def _pick_movie_status(rows: list[Any]) -> str | None:
    statuses: list[str] = [
        str(r["movie_status"]).lower() for r in rows if r["movie_status"] is not None
    ]
    if not statuses:
        return None

    def _priority(s: str) -> int:
        try:
            return STATUS_PRIORITY.get(WatchStatus(s), 0)
        except ValueError:
            return 0

    return max(statuses, key=_priority)


def _to_percent(v: float | None) -> int | None:
    # rating_value хранит шкалу 0..10 (TMDB, Sonarr, Radarr)
    return None if v is None else round(v * 10)


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
            watch_status = _pick_movie_status(media_rows)

        if status and watch_status != status:
            continue

        genres = row["genres"] or []
        media_type_item = cast(Literal["movie", "series"], media_type_val.lower())
        watch_status_item = cast(
            Literal["watched", "watching", "planned", "dropped"] | None, watch_status
        )
        items.append(
            MediaItem(
                id=media_id,
                title=row["title"],
                media_type=media_type_item,
                year=row["year"],
                genres=genres,
                poster_url=row["poster_url"],
                rating=row["rating"],
                watch_status=watch_status_item,
                total_episodes=row["total_count"] if media_type_val == "SERIES" else None,
                watched_episodes=(
                    (row["watched_count"] or 0) if media_type_val == "SERIES" else None
                ),
            )
        )

    return MediaListResponse(items=items, total=len(items))


async def get_media_detail_by_id(
    session: AsyncSession,
    media_id: int,
) -> MediaDetailResponse:
    query = text(
        """
        SELECT
            m.id,
            m.title,
            m.media_type,
            COALESCE(mov.year, s.year) AS year,
            COALESCE(mov.genres, s.genres) AS genres,
            COALESCE(mov.poster_url, s.poster_url) AS poster_url,
            COALESCE(mov.backdrop_path, s.backdrop_path) AS backdrop_path,
            COALESCE(mov.overview, s.overview) AS overview,
            COALESCE(mov.rating_value, s.rating_value) AS rating_value,
            COALESCE(mov.tmdb_id, s.tmdb_id) AS tmdb_id,
            COALESCE(mov.imdb_id, s.imdb_id) AS imdb_id,
            s.tvdb_id AS tvdb_id,
            mov.status AS movie_release_status,
            s.status AS series_status,
            movie_wh.status AS movie_status,
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
        LEFT JOIN LATERAL (
            SELECT
                COUNT(e.id) AS total_count,
                COUNT(*) FILTER (WHERE wh.status = 'WATCHED') AS watched_count,
                COUNT(*) FILTER (WHERE wh.status = 'WATCHING') AS watching_count,
                COUNT(*) FILTER (WHERE wh.status = 'DROPPED') AS dropped_count
            FROM seasons sea
            JOIN episodes e ON e.season_id = sea.id
            LEFT JOIN watch_history wh ON wh.episode_id = e.id
            WHERE sea.series_id = m.id
        ) ep_stats ON m.media_type = 'SERIES'
        WHERE m.id = :media_id
        """
    )

    rows = (await session.execute(query, {"media_id": media_id})).mappings().all()

    if not rows:
        raise HTTPException(status_code=404, detail="Media not found")

    row = rows[0]
    media_type_val: str = row["media_type"]
    media_type_lower = media_type_val.lower()

    if media_type_val == "MOVIE":
        raw_status = row["movie_release_status"]
        status_val = None if raw_status is None else raw_status.lower()
        watch_status = _pick_movie_status(list(rows))
        tvdb_id = None
    else:
        raw_status = row["series_status"]
        status_val = None if raw_status is None else raw_status.lower()
        total = row["total_count"] or 0
        watched = row["watched_count"] or 0
        watching = row["watching_count"] or 0
        dropped = row["dropped_count"] or 0
        watch_status = compute_series_status(watched, watching, dropped, total)
        tvdb_id = row["tvdb_id"]

    seasons: list[SeasonDetail] = []
    if media_type_val == "SERIES":
        seasons_query = text(
            """
            SELECT
                sea.number,
                sea.poster_url,
                sea.vote_average,
                sea.release_date,
                COUNT(e.id) AS total_episodes,
                COUNT(*) FILTER (WHERE wh.status = 'WATCHED') AS watched_episodes
            FROM seasons sea
            LEFT JOIN episodes e ON e.season_id = sea.id
            LEFT JOIN watch_history wh ON wh.episode_id = e.id
            WHERE sea.series_id = :media_id
            GROUP BY sea.id, sea.number, sea.poster_url, sea.vote_average, sea.release_date
            ORDER BY sea.number
            """
        )
        season_rows = (
            (await session.execute(seasons_query, {"media_id": media_id})).mappings().all()
        )
        seasons = [
            SeasonDetail(
                number=s["number"],
                poster_url=s["poster_url"],
                vote_average=s["vote_average"],
                release_date=s["release_date"],
                total_episodes=s["total_episodes"] or 0,
                watched_episodes=s["watched_episodes"] or 0,
            )
            for s in season_rows
        ]

    media_type_typed = cast(Literal["movie", "series"], media_type_lower)
    watch_status_typed = cast(
        Literal["watched", "watching", "planned", "dropped"] | None, watch_status
    )
    return MediaDetailResponse(
        id=row["id"],
        media_type=media_type_typed,
        title=row["title"],
        year=row["year"],
        poster_url=row["poster_url"],
        backdrop_path=row["backdrop_path"],
        overview=row["overview"],
        genres=row["genres"] or [],
        status=status_val,
        tmdb_rating_percent=_to_percent(row["rating_value"]),
        watch_status=watch_status_typed,
        tmdb_id=row["tmdb_id"],
        imdb_id=row["imdb_id"],
        tvdb_id=tvdb_id,
        seasons=seasons,
    )
