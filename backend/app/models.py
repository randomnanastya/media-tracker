from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Boolean
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()

class MediaType(enum.Enum):
    MOVIE = "movie"
    SERIES = "series"

class Media(Base):
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(MediaType), nullable=False)
    title = Column(String, nullable=False)
    release_date = Column(DateTime, nullable=True)

    # связи
    series = relationship("Series", back_populates="media", uselist=False)
    movie = relationship("Movie", back_populates="media", uselist=False)

class Series(Base):
    __tablename__ = "series"

    id = Column(Integer, ForeignKey("media.id"), primary_key=True)
    media = relationship("Media", back_populates="series")
    seasons = relationship("Season", back_populates="series")

class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, ForeignKey("media.id"), primary_key=True)
    media = relationship("Media", back_populates="movie")

class Season(Base):
    __tablename__ = "seasons"

    id = Column(Integer, primary_key=True)
    series_id = Column(Integer, ForeignKey("series.id"), nullable=False)
    number = Column(Integer, nullable=False)
    release_date = Column(DateTime, nullable=True)

    series = relationship("Series", back_populates="seasons")
    episodes = relationship("Episode", back_populates="season")

class Episode(Base):
    __tablename__ = "episodes"

    id = Column(Integer, primary_key=True)
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False)
    number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    watched = Column(Boolean, default=False)
    watched_at = Column(DateTime, nullable=True)

    season = relationship("Season", back_populates="episodes")
