import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class MediaType(enum.Enum):
    MOVIE = "movie"
    SERIES = "series"


class MovieStatus(enum.Enum):
    RUMORED = "rumored"
    ANNOUNCED = "announced"
    IN_PRODUCTION = "in_production"
    POST_PRODUCTION = "post_production"
    IN_CINEMAS = "in_cinemas"
    RELEASED = "released"
    CANCELED = "canceled"


class SeriesStatus(enum.Enum):
    CONTINUING = "continuing"
    IN_PRODUCTION = "in_production"
    PLANNED = "planned"
    ENDED = "ended"
    CANCELED = "canceled"
    DELETED = "deleted"


class Media(Base):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    release_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

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
    jellyfin_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    status: Mapped[SeriesStatus | None] = mapped_column(Enum(SeriesStatus), nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String)
    year: Mapped[int | None] = mapped_column(Integer)
    genres: Mapped[list[str] | None] = mapped_column(JSON)
    rating_value: Mapped[float | None] = mapped_column(Float)
    rating_votes: Mapped[int | None] = mapped_column(Integer)
    original_name: Mapped[str | None] = mapped_column(String, nullable=True)
    overview: Mapped[str | None] = mapped_column(String, nullable=True)
    backdrop_path: Mapped[str | None] = mapped_column(String, nullable=True)
    first_air_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_air_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tmdb_metadata_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    number_of_seasons: Mapped[int | None] = mapped_column(Integer, nullable=True)
    number_of_episodes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    media: Mapped["Media"] = relationship("Media", back_populates="series")
    seasons: Mapped[list["Season"]] = relationship("Season", back_populates="series")


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, ForeignKey("media.id"), primary_key=True)
    radarr_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    tmdb_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    imdb_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    jellyfin_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    status: Mapped[MovieStatus | None] = mapped_column(Enum(MovieStatus), nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String)
    year: Mapped[int | None] = mapped_column(Integer)
    genres: Mapped[list[str] | None] = mapped_column(JSON)
    rating_value: Mapped[float | None] = mapped_column(Float)
    rating_votes: Mapped[int | None] = mapped_column(Integer)
    original_title: Mapped[str | None] = mapped_column(String, nullable=True)
    overview: Mapped[str | None] = mapped_column(String, nullable=True)
    backdrop_path: Mapped[str | None] = mapped_column(String, nullable=True)
    tmdb_metadata_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    media: Mapped["Media"] = relationship("Media", back_populates="movie")


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(Integer, ForeignKey("series.id"), nullable=False)
    jellyfin_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    release_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tmdb_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    overview: Mapped[str | None] = mapped_column(String, nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String, nullable=True)
    vote_average: Mapped[float | None] = mapped_column(Float, nullable=True)

    series: Mapped["Series"] = relationship("Series", back_populates="seasons")
    episodes: Mapped[list["Episode"]] = relationship("Episode", back_populates="season")


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    sonarr_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    jellyfin_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    air_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    overview: Mapped[str | None] = mapped_column(String)
    tmdb_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    episode_type: Mapped[str | None] = mapped_column(String, nullable=True)
    still_url: Mapped[str | None] = mapped_column(String, nullable=True)
    vote_average: Mapped[float | None] = mapped_column(Float, nullable=True)

    season: Mapped["Season"] = relationship("Season", back_populates="episodes")
