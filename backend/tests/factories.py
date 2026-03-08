import random
import uuid
from datetime import UTC, datetime

import factory
from factory import LazyAttribute, LazyFunction, Sequence, SubFactory
from faker import Faker

from app.models import Episode, Media, MediaType, Movie, Season, Series, User, WatchHistory

fake = Faker()


class MediaFactory(factory.Factory):
    class Meta:
        model = Media

    id = Sequence(lambda n: n + 1)
    media_type = MediaType.MOVIE
    title = Sequence(lambda n: f"Test Movie {n}")
    release_date = factory.LazyFunction(lambda: datetime(2023, 1, 1, tzinfo=UTC))


class MovieFactory(factory.Factory):
    class Meta:
        model = Movie

    id = Sequence(lambda n: n + 1)
    jellyfin_id = None
    radarr_id = Sequence(lambda n: n + 100)
    tmdb_id = Sequence(lambda n: str(12345 + n))
    imdb_id = Sequence(lambda n: f"t{1000000 + n}")
    media = SubFactory(MediaFactory)


class RadarrMovieDictFactory(factory.DictFactory):
    id = Sequence(lambda n: n + 1)
    title = Sequence(lambda n: f"Test Movie {n}")
    inCinemas = LazyFunction(
        lambda: fake.date_time_between(start_date="-10y", end_date="now").strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    )
    year = LazyAttribute(lambda obj: int(obj.inCinemas[:4]) if obj.inCinemas else None)
    tmdbId = Sequence(lambda n: 12345 + n)
    imdbId = Sequence(lambda n: f"tt{1000000 + n}")
    path = LazyAttribute(lambda obj: f"/movies/{obj.title}")

    class Params:
        no_date = factory.Trait(inCinemas=None, year=None)
        invalid_date = factory.Trait(inCinemas="invalid-date-string")
        missing_id = factory.Trait(id=None)
        no_tmdb = factory.Trait(tmdbId=None)
        no_imdb = factory.Trait(imdbId=None)
        no_external_ids = factory.Trait(tmdbId=None, imdbId=None)
        special_chars = factory.Trait(title="Movie with spéciål chàrs")
        cyrillic = factory.Trait(title="Фільм з кириличними символами 🎬")
        empty_title = factory.Trait(title="")
        very_long_title = factory.Trait(title="A" * 500)
        negative_id = factory.Trait(id=-1)
        zero_year = factory.Trait(year=0)


class SeriesFactory(factory.Factory):
    class Meta:
        model = Series

    id = Sequence(lambda n: n + 1)
    sonarr_id = Sequence(lambda n: n + 100)
    tvdb_id = Sequence(lambda n: str(123456 + n))
    tmdb_id = Sequence(lambda n: str(12345 + n))
    imdb_id = Sequence(lambda n: f"tt{1000000 + n}")
    jellyfin_id = LazyFunction(lambda: str(uuid.uuid4()))
    status = "continuing"
    poster_url = "https://artworks.thetvdb.com/banners/v4/series/415089/posters/63e7c53b4c2a8.jpg"
    year = LazyAttribute(lambda _: fake.random_int(min=1930, max=2030))
    genres = LazyFunction(
        lambda: random.sample(
            [
                "Action",
                "Adventure",
                "Animation",
                "Biography",
                "Comedy",
                "Crime",
                "Documentary",
                "Drama",
                "Family",
                "Fantasy",
                "Film Noir",
                "History",
                "Horror",
                "Music",
                "Musical",
                "Mystery",
                "Romance",
                "Sci-Fi",
                "Sport",
                "Thriller",
                "War",
                "Western",
            ],
            k=random.randint(1, 4),
        )
    )
    rating_value = LazyFunction(lambda: round(fake.pyfloat(min_value=1, max_value=10), 1))
    rating_votes = LazyFunction(lambda: fake.random_int(min=1, max=10000))

    media = SubFactory(
        MediaFactory, media_type=MediaType.SERIES, title=Sequence(lambda n: f"Test Series {n}")
    )

    class Params:
        no_ids = factory.Trait(
            jellyfin_id=None, tvdb_id=None, imdb_id=None, tmdb_id=None, sonarr_id=None
        )
        ended = factory.Trait(status="ended")


class SeasonFactory(factory.Factory):
    class Meta:
        model = Season

    id = Sequence(lambda n: n + 1)
    series_id = 1  # По умолчанию, можно переопределить
    jellyfin_id = LazyFunction(lambda: str(uuid.uuid4()))
    number = Sequence(lambda n: n)
    release_date = LazyFunction(
        lambda: fake.date_time_between(start_date="-10y", end_date="now").replace(tzinfo=UTC)
    )

    class Params:
        no_jellyfin_id = factory.Trait(jellyfin_id=None)
        no_date = factory.Trait(release_date=None)


class EpisodeFactory(factory.Factory):
    class Meta:
        model = Episode

    id = Sequence(lambda n: n + 1)
    season_id = 1  # По умолчанию, можно переопределить
    sonarr_id = Sequence(lambda n: n + 100)
    jellyfin_id = LazyFunction(lambda: str(uuid.uuid4()))
    number = Sequence(lambda n: n)
    title = Sequence(lambda n: f"Episode {n}")
    air_date = LazyFunction(
        lambda: fake.date_time_between(start_date="-5y", end_date="now").replace(tzinfo=UTC)
    )
    overview = LazyFunction(lambda: fake.text(max_nb_chars=200))

    class Params:
        no_ids = factory.Trait(sonarr_id=None, jellyfin_id=None)
        no_date = factory.Trait(air_date=None)
        no_overview = factory.Trait(overview=None)


class UserFactory(factory.Factory):
    class Meta:
        model = User

    id = Sequence(lambda n: n + 1)
    username = Sequence(lambda n: f"user_{n}")
    jellyfin_user_id = LazyFunction(lambda: str(uuid.uuid4()))

    class Params:
        no_jellyfin_id = factory.Trait(jellyfin_user_id=None)


class WatchHistoryFactory(factory.Factory):
    class Meta:
        model = WatchHistory

    id = Sequence(lambda n: n + 1)
    user_id = 1  # По умолчанию, можно переопределить
    media_id = 1  # По умолчанию, можно переопределить
    episode_id = None  # None для фильмов, заполняется для сериалов
    is_watched = True
    watched_at = LazyFunction(
        lambda: fake.date_time_between(start_date="-2y", end_date="now").replace(tzinfo=UTC)
    )

    class Params:
        movie_watch = factory.Trait(episode_id=None)
        series_watch = factory.Trait(episode_id=1)
        not_watched = factory.Trait(is_watched=False, watched_at=None)


# === Dict Factories для API responses ===


class SeriesDictFactory(factory.DictFactory):
    id = Sequence(lambda n: n + 1)
    title = Sequence(lambda n: f"Test Series {n}")
    overview = LazyFunction(lambda: fake.text(max_nb_chars=200))
    firstAired = LazyFunction(
        lambda: fake.date_time_between(start_date="-10y", end_date="now").strftime("%Y-%m-%d")
    )
    year = LazyAttribute(lambda obj: int(obj.firstAired[:4]) if obj.firstAired else None)
    status = "continuing"
    network = LazyFunction(lambda: fake.company())
    runtime = LazyFunction(lambda: fake.random_int(min=20, max=60))

    # ID различных сервисов
    tvdbId = Sequence(lambda n: 123456 + n)
    tmdbId = Sequence(lambda n: 12345 + n)
    imdbId = Sequence(lambda n: f"tt{1000000 + n}")

    # Рейтинги
    rating = LazyFunction(
        lambda: {
            "value": round(fake.pyfloat(min_value=1, max_value=10), 1),
            "votes": fake.random_int(min=1, max=10000),
        }
    )

    # Жанры
    genres = LazyFunction(
        lambda: random.sample(
            [
                "Action",
                "Adventure",
                "Animation",
                "Biography",
                "Comedy",
                "Crime",
                "Documentary",
                "Drama",
                "Family",
                "Fantasy",
                "Film Noir",
                "History",
                "Horror",
                "Music",
                "Musical",
                "Mystery",
                "Romance",
                "Sci-Fi",
                "Sport",
                "Thriller",
                "War",
                "Western",
            ],
            k=random.randint(1, 5),
        )
    )

    # Постер
    poster = "https://artworks.thetvdb.com/banners/v4/series/415089/posters/63e7c53b4c2a8.jpg"

    class Params:
        no_date = factory.Trait(firstAired=None, year=None)
        invalid_date = factory.Trait(firstAired="invalid-date", year=None)
        ended = factory.Trait(
            status="ended",
            lastAired=LazyFunction(
                lambda: fake.date_time_between(start_date="-5y", end_date="now").strftime(
                    "%Y-%m-%d"
                )
            ),
        )
        no_tvdb = factory.Trait(tvdbId=None)
        no_tmdb = factory.Trait(tmdbId=None)
        no_imdb = factory.Trait(imdbId=None)
        no_external_ids = factory.Trait(tvdbId=None, tmdbId=None, imdbId=None)
        no_genres = factory.Trait(genres=[])
        no_rating = factory.Trait(rating={"value": 0, "votes": 0})
        empty_title = factory.Trait(title="")
        empty_overview = factory.Trait(overview="")
        very_long_title = factory.Trait(title="Series " + "X" * 500)
        unicode_title = factory.Trait(title="Серіал 📺 with émojis ✨")
        negative_id = factory.Trait(id=-1)


class SeasonDictFactory(factory.DictFactory):
    seasonNumber = Sequence(lambda n: n)
    statistics = LazyFunction(
        lambda: {
            "episodeCount": fake.random_int(min=1, max=24),
            "totalEpisodeCount": fake.random_int(min=1, max=24),
        }
    )


class SonarrEpisodeDictFactory(factory.DictFactory):
    """Фабрика для эпизодов из Sonarr API."""

    id = Sequence(lambda n: n + 100)
    seriesId = 1  # По умолчанию, можно переопределить
    seasonNumber = 1
    episodeNumber = Sequence(lambda n: n)
    title = Sequence(lambda n: f"Episode {n}")
    airDateUtc = LazyFunction(
        lambda: fake.date_time_between(start_date="-5y", end_date="now").strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    )
    overview = LazyFunction(lambda: fake.text(max_nb_chars=200))
    hasFile = True
    monitored = True

    class Params:
        no_date = factory.Trait(airDateUtc=None)
        no_overview = factory.Trait(overview=None)
        no_file = factory.Trait(hasFile=False)


# === Jellyfin API Dict Factories ===


class JellyfinMovieDictFactory(factory.DictFactory):
    """Фабрика для фильмов из Jellyfin API."""

    Id = LazyFunction(lambda: str(uuid.uuid4()))
    Name = Sequence(lambda n: f"Movie {n}")
    PremiereDate = LazyFunction(
        lambda: fake.date_time_between(start_date="-10y", end_date="now").strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    )
    ProviderIds = LazyFunction(
        lambda: {
            "Tmdb": str(fake.random_int(10000, 99999)),
            "Imdb": f"tt{fake.random_int(1000000, 9999999)}",
        }
    )
    Type = "Movie"

    class Params:
        no_date = factory.Trait(PremiereDate=None)
        no_providers = factory.Trait(ProviderIds={})
        only_tmdb = factory.Trait(
            ProviderIds=LazyFunction(lambda: {"Tmdb": str(fake.random_int(10000, 99999))})
        )
        only_imdb = factory.Trait(
            ProviderIds=LazyFunction(lambda: {"Imdb": f"tt{fake.random_int(1000000, 9999999)}"})
        )
        empty_name = factory.Trait(Name="")
        very_long_name = factory.Trait(Name="Movie " + "M" * 500)
        unicode_name = factory.Trait(Name="Кіно 🎬 со спецсимволами ñ ü")


class JellyfinSeriesDictFactory(factory.DictFactory):
    """Фабрика для сериалов из Jellyfin API."""

    Id = LazyFunction(lambda: str(uuid.uuid4()))
    Name = Sequence(lambda n: f"Series {n}")
    PremiereDate = LazyFunction(
        lambda: fake.date_time_between(start_date="-10y", end_date="now").strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    )
    ProviderIds = LazyFunction(
        lambda: {
            "Tmdb": str(fake.random_int(10000, 99999)),
            "Imdb": f"tt{fake.random_int(1000000, 9999999)}",
            "Tvdb": str(fake.random_int(100000, 999999)),
        }
    )
    Type = "Series"
    Status = "Continuing"

    class Params:
        no_date = factory.Trait(PremiereDate=None)
        no_providers = factory.Trait(ProviderIds={})
        ended = factory.Trait(Status="Ended")
        empty_name = factory.Trait(Name="")
        very_long_name = factory.Trait(Name="Series " + "S" * 500)
        unicode_name = factory.Trait(Name="Серіал 📺 з емодзі 🎭")


class JellyfinEpisodeDictFactory(factory.DictFactory):
    """Фабрика для эпизодов из Jellyfin API."""

    Id = LazyFunction(lambda: str(uuid.uuid4()))
    Name = Sequence(lambda n: f"Episode {n}")
    ParentIndexNumber = 1  # номер сезона
    IndexNumber = Sequence(lambda n: n)  # номер эпизода
    PremiereDate = LazyFunction(
        lambda: fake.date_time_between(start_date="-5y", end_date="now").strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    )
    SeasonId = LazyFunction(lambda: str(uuid.uuid4()))
    SeriesId = LazyFunction(lambda: str(uuid.uuid4()))
    Type = "Episode"

    class Params:
        no_date = factory.Trait(PremiereDate=None)
        no_season_number = factory.Trait(ParentIndexNumber=None)


class JellyfinUserDictFactory(factory.DictFactory):
    """Фабрика для пользователей из Jellyfin API."""

    Id = LazyFunction(lambda: str(uuid.uuid4()))
    Name = Sequence(lambda n: f"User_{n}")
    ServerId = LazyFunction(lambda: str(uuid.uuid4()))
    HasPassword = True
    HasConfiguredPassword = True

    class Params:
        no_password = factory.Trait(HasPassword=False, HasConfiguredPassword=False)
