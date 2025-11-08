import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class MediaType(enum.Enum):
    MOVIE = "movie"
    SERIES = "series"


class Media(Base):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    release_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # связи
    series: Mapped[Optional["Series"]] = relationship(
        "Series", back_populates="media", uselist=False
    )
    movie: Mapped[Optional["Movie"]] = relationship("Movie", back_populates="media", uselist=False)


class Series(Base):
    __tablename__ = "series"

    id: Mapped[int] = mapped_column(Integer, ForeignKey("media.id"), primary_key=True)
    sonarr_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    tvdb_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    tmdb_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    imdb_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    jellyfin_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String)
    year: Mapped[int | None] = mapped_column(Integer)
    genres: Mapped[list[str] | None] = mapped_column(JSON)
    rating_value: Mapped[float | None] = mapped_column(Float)
    rating_votes: Mapped[int | None] = mapped_column(Integer)

    media: Mapped["Media"] = relationship("Media", back_populates="series")
    seasons: Mapped[list["Season"]] = relationship("Season", back_populates="series")


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, ForeignKey("media.id"), primary_key=True)
    radarr_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    tmdb_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    imdb_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    jellyfin_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)

    media: Mapped["Media"] = relationship("Media", back_populates="movie")


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(Integer, ForeignKey("series.id"), nullable=False)
    jellyfin_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    release_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    series: Mapped["Series"] = relationship("Series", back_populates="seasons")
    episodes: Mapped[list["Episode"]] = relationship("Episode", back_populates="season")


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    sonarr_id: Mapped[int] = mapped_column(Integer, unique=True)
    jellyfin_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    air_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    overview: Mapped[str | None] = mapped_column(String)

    season: Mapped["Season"] = relationship("Season", back_populates="episodes")


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

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    media_id: Mapped[int] = mapped_column(Integer, ForeignKey("media.id"), nullable=False)
    episode_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("episodes.id"), nullable=True
    )
    watched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="watch_history")
    media: Mapped["Media"] = relationship("Media")
    episode: Mapped[Optional["Episode"]] = relationship("Episode")
