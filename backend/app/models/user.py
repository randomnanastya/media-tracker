import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.media import Episode, Media


class WatchStatus(enum.Enum):
    PLANNED = "planned"
    WATCHING = "watching"
    WATCHED = "watched"
    DROPPED = "dropped"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    jellyfin_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, unique=True)

    watch_history: Mapped[list["WatchHistory"]] = relationship(
        "WatchHistory", back_populates="user"
    )


class WatchHistory(Base):
    __tablename__ = "watch_history"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "media_id", "episode_id", name="uq_watch_history_user_media_episode"
        ),
        Index(
            "uq_watch_history_user_media_no_episode",
            "user_id",
            "media_id",
            unique=True,
            postgresql_where=text("episode_id IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    media_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("media.id"), nullable=False, index=True
    )
    episode_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("episodes.id"),
        nullable=True,
        index=True,
    )
    status: Mapped[WatchStatus] = mapped_column(
        Enum(WatchStatus), nullable=False, default=WatchStatus.PLANNED
    )
    is_manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    playback_position_ticks: Mapped[int | None] = mapped_column(BigInteger)
    watched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship("User", back_populates="watch_history")
    media: Mapped["Media"] = relationship("Media")
    episode: Mapped[Optional["Episode"]] = relationship("Episode")
