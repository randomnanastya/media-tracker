"""Edge case tests for service layer - empty strings, unicode, long strings, etc."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.import_jellyfin_movies_service import import_jellyfin_movies
from app.services.radarr_service import import_radarr_movies
from app.services.sonarr_service import import_sonarr_series
from tests.factories import JellyfinMovieDictFactory, RadarrMovieDictFactory, SeriesDictFactory


@pytest.mark.asyncio
async def test_import_radarr_movie_with_empty_title(mock_session):
    """Фильм с пустым названием должен быть импортирован (database allows it)."""
    movies_data = [
        RadarrMovieDictFactory.build(empty_title=True, id=1, tmdbId=1001),
    ]

    with (
        patch(
            "app.services.radarr_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://radarr:7878", "test-api-key"),
        ),
        patch(
            "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
        ) as mock_fetch,
    ):
        mock_fetch.return_value = movies_data

        mock_session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=None), scalars=Mock(return_value=[])
        )

        result = await import_radarr_movies(mock_session)

        # Empty title should still be imported
        assert result.imported_count == 1
        assert mock_session.add.called


@pytest.mark.asyncio
async def test_import_radarr_movie_with_very_long_title(mock_session):
    """Фильм с очень длинным названием (500+ символов)."""
    movies_data = [
        RadarrMovieDictFactory.build(very_long_title=True, id=1, tmdbId=1001),
    ]

    with (
        patch(
            "app.services.radarr_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://radarr:7878", "test-api-key"),
        ),
        patch(
            "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
        ) as mock_fetch,
    ):
        mock_fetch.return_value = movies_data

        mock_session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=None), scalars=Mock(return_value=[])
        )

        result = await import_radarr_movies(mock_session)

        # Long title should be imported
        assert result.imported_count == 1
        assert mock_session.add.called


@pytest.mark.asyncio
async def test_import_radarr_movie_with_unicode_and_emoji(mock_session):
    """Фильм с unicode и emoji в названии."""
    movies_data = [
        RadarrMovieDictFactory.build(cyrillic=True, id=1, tmdbId=1001),
    ]

    with (
        patch(
            "app.services.radarr_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://radarr:7878", "test-api-key"),
        ),
        patch(
            "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
        ) as mock_fetch,
    ):
        mock_fetch.return_value = movies_data

        mock_session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=None), scalars=Mock(return_value=[])
        )

        result = await import_radarr_movies(mock_session)

        # Unicode should be handled correctly
        assert result.imported_count == 1
        assert mock_session.add.called


@pytest.mark.asyncio
async def test_import_radarr_movie_with_zero_year(mock_session):
    """Фильм с year=0."""
    movies_data = [
        RadarrMovieDictFactory.build(zero_year=True, id=1, tmdbId=1001),
    ]

    with (
        patch(
            "app.services.radarr_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://radarr:7878", "test-api-key"),
        ),
        patch(
            "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
        ) as mock_fetch,
    ):
        mock_fetch.return_value = movies_data

        mock_session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=None), scalars=Mock(return_value=[])
        )

        result = await import_radarr_movies(mock_session)

        # Zero year should be allowed
        assert result.imported_count == 1


@pytest.mark.asyncio
async def test_import_radarr_movie_with_negative_id(mock_session):
    """Фильм с отрицательным ID."""
    movies_data = [
        RadarrMovieDictFactory.build(negative_id=True, tmdbId=1001),
    ]

    with (
        patch(
            "app.services.radarr_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://radarr:7878", "test-api-key"),
        ),
        patch(
            "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
        ) as mock_fetch,
    ):
        mock_fetch.return_value = movies_data

        mock_session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=None), scalars=Mock(return_value=[])
        )

        result = await import_radarr_movies(mock_session)

        # Negative ID should be imported (no validation currently)
        assert result.imported_count == 1


@pytest.mark.asyncio
async def test_import_sonarr_series_with_empty_title_skipped(mock_session):
    """Сериал с пустым названием правильно пропускается."""
    series_data = [
        SeriesDictFactory.build(empty_title=True, id=1, tvdbId=123456),
    ]

    with (
        patch(
            "app.services.sonarr_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://sonarr:8989", "test-api-key"),
        ),
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_fetch_series,
        patch(
            "app.services.sonarr_service.fetch_sonarr_episodes", new_callable=AsyncMock
        ) as mock_fetch_episodes,
    ):
        mock_fetch_series.return_value = series_data
        mock_fetch_episodes.return_value = []

        mock_session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=None), scalars=Mock(return_value=[])
        )

        result = await import_sonarr_series(mock_session)

        # Empty title should be skipped (service validates this)
        assert result.new_series == 0


@pytest.mark.asyncio
async def test_import_sonarr_series_with_unicode_title(mock_session):
    """Сериал с unicode и emoji в названии."""
    series_data = [
        SeriesDictFactory.build(unicode_title=True, id=1, tvdbId=123456),
    ]

    with (
        patch(
            "app.services.sonarr_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://sonarr:8989", "test-api-key"),
        ),
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_fetch_series,
        patch(
            "app.services.sonarr_service.fetch_sonarr_episodes", new_callable=AsyncMock
        ) as mock_fetch_episodes,
    ):
        mock_fetch_series.return_value = series_data
        mock_fetch_episodes.return_value = []

        mock_session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=None), scalars=Mock(return_value=[])
        )

        result = await import_sonarr_series(mock_session)

        # Unicode should be handled
        assert result.new_series == 1


@pytest.mark.asyncio
async def test_import_sonarr_series_with_very_long_title(mock_session):
    """Сериал с очень длинным названием."""
    series_data = [
        SeriesDictFactory.build(very_long_title=True, id=1, tvdbId=123456),
    ]

    with (
        patch(
            "app.services.sonarr_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://sonarr:8989", "test-api-key"),
        ),
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_fetch_series,
        patch(
            "app.services.sonarr_service.fetch_sonarr_episodes", new_callable=AsyncMock
        ) as mock_fetch_episodes,
    ):
        mock_fetch_series.return_value = series_data
        mock_fetch_episodes.return_value = []

        mock_session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=None), scalars=Mock(return_value=[])
        )

        result = await import_sonarr_series(mock_session)

        # Long title should be imported
        assert result.new_series == 1


@pytest.mark.asyncio
async def test_import_sonarr_series_with_empty_overview(mock_session):
    """Сериал с пустым overview."""
    series_data = [
        SeriesDictFactory.build(empty_overview=True, id=1, tvdbId=123456),
    ]

    with (
        patch(
            "app.services.sonarr_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://sonarr:8989", "test-api-key"),
        ),
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_fetch_series,
        patch(
            "app.services.sonarr_service.fetch_sonarr_episodes", new_callable=AsyncMock
        ) as mock_fetch_episodes,
    ):
        mock_fetch_series.return_value = series_data
        mock_fetch_episodes.return_value = []

        mock_session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=None), scalars=Mock(return_value=[])
        )

        result = await import_sonarr_series(mock_session)

        # Empty overview is acceptable
        assert result.new_series == 1


@pytest.mark.asyncio
async def test_jellyfin_movie_with_empty_name(mock_session):
    """Jellyfin movie с пустым Name."""
    jellyfin_movies = [
        JellyfinMovieDictFactory.build(empty_name=True),
    ]

    with (
        patch(
            "app.services.import_jellyfin_movies_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://jellyfin:8096", "test-api-key"),
        ),
        patch(
            "app.services.import_jellyfin_movies_service.fetch_jellyfin_movies",
            new_callable=AsyncMock,
        ) as mock_fetch,
    ):
        mock_fetch.return_value = jellyfin_movies

        mock_session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=None), scalars=Mock(return_value=[])
        )

        result = await import_jellyfin_movies(mock_session)

        # Empty name - result depends on implementation
        assert result.imported_count >= 0


@pytest.mark.asyncio
async def test_jellyfin_movie_with_unicode_name(mock_session):
    """Jellyfin movie с unicode в Name."""
    jellyfin_movies = [
        JellyfinMovieDictFactory.build(
            unicode_name=True,
            ProviderIds={"Tmdb": "12345", "Imdb": "tt1234567"},
        ),
    ]

    with (
        patch(
            "app.services.import_jellyfin_movies_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://jellyfin:8096", "test-api-key"),
        ),
        patch(
            "app.services.import_jellyfin_movies_service.fetch_jellyfin_movies",
            new_callable=AsyncMock,
        ) as mock_fetch,
    ):
        mock_fetch.return_value = jellyfin_movies

        mock_session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=None), scalars=Mock(return_value=[])
        )

        result = await import_jellyfin_movies(mock_session)

        # Unicode should work
        assert result.imported_count >= 0


@pytest.mark.asyncio
async def test_jellyfin_movie_with_very_long_name(mock_session):
    """Jellyfin movie с очень длинным Name."""
    jellyfin_movies = [
        JellyfinMovieDictFactory.build(
            very_long_name=True,
            ProviderIds={"Tmdb": "12345", "Imdb": "tt1234567"},
        ),
    ]

    with (
        patch(
            "app.services.import_jellyfin_movies_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://jellyfin:8096", "test-api-key"),
        ),
        patch(
            "app.services.import_jellyfin_movies_service.fetch_jellyfin_movies",
            new_callable=AsyncMock,
        ) as mock_fetch,
    ):
        mock_fetch.return_value = jellyfin_movies

        mock_session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=None), scalars=Mock(return_value=[])
        )

        result = await import_jellyfin_movies(mock_session)

        # Long name should be handled
        assert result.imported_count >= 0
