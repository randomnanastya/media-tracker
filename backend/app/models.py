from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Boolean
from sqlalchemy.orm import declarative_base, relationship
import enum

from sqlalchemy.sql import func

Base = declarative_base()

class MediaType(enum.Enum):
    MOVIE = "movie"
    SERIES = "series"

class Media(Base):
    __tablename__: str = "media"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(MediaType), nullable=False)
    title = Column(String, nullable=False)
    release_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    # связи
    series = relationship("Series", back_populates="media", uselist=False)
    movie = relationship("Movie", back_populates="media", uselist=False)

class Series(Base):
    __tablename__: str = "series"

    id = Column(Integer, ForeignKey("media.id"), primary_key=True)
    jellyfin_id = Column(Integer, nullable=True, unique=True)
    status = Column(String, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    media = relationship("Media", back_populates="series")
    seasons = relationship("Season", back_populates="series")

class Movie(Base):
    __tablename__: str = "movies"

    id = Column(Integer, ForeignKey("media.id"), primary_key=True)
    radarr_id = Column(Integer, nullable=True, unique=True)
    watched = Column(Boolean, default=False)
    watched_at = Column(DateTime(timezone=True), nullable=True)

    media = relationship("Media", back_populates="movie")

class Season(Base):
    __tablename__: str = "seasons"

    id = Column(Integer, primary_key=True)
    series_id = Column(Integer, ForeignKey("series.id"), nullable=False)
    jellyfin_id = Column(Integer, nullable=True, unique=True)
    number = Column(Integer, nullable=False)
    release_date = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    series = relationship("Series", back_populates="seasons")
    episodes = relationship("Episode", back_populates="season")

class Episode(Base):
    __tablename__: str = "episodes"

    id = Column(Integer, primary_key=True)
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False)
    jellyfin_id = Column(Integer, nullable=True, unique=True)
    number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    air_date = Column(DateTime(timezone=True), nullable=True)
    watched = Column(Boolean, default=False)
    watched_at = Column(DateTime(timezone=True), nullable=True)

    season = relationship("Season", back_populates="episodes")

class User(Base):
    __tablename__: str = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    jellyfin_user_id = Column(Integer, nullable=True, unique=True)

    watch_history = relationship("WatchHistory", back_populates="user")

class WatchHistory(Base):
    __tablename__: str = "watch_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    media_id = Column(Integer, ForeignKey("media.id"), nullable=False)
    episode_id = Column(Integer, ForeignKey("episodes.id"), nullable=True)
    watched_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="watch_history")
    media = relationship("Media")
    episode = relationship("Episode")
