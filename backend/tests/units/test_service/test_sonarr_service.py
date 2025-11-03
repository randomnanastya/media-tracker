from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.exceptions.client_errors import ClientError
from app.models import Episode, Season, Series
from app.schemas.error_codes import SonarrErrorCode
from app.schemas.sonarr import SonarrImportResponse
from app.services.sonarr_service import import_sonarr_series


def calculate_expected_entities_count(series_count, episodes_data):
    unique_seasons = len({ep["seasonNumber"] for ep in episodes_data}) if episodes_data else 0
    episodes_count = len(episodes_data)
    return (
        (series_count * 2) + unique_seasons + episodes_count
    )  # Media + Series + Seasons + Episodes


@pytest.mark.asyncio
async def test_import_sonarr_series_creates_entities(
    mock_session, sonarr_series_basic, sonarr_episodes_basic, mock_exists_result_false
):
    """Test service creates Media, Series, Season, and Episode entities for new series."""
    # Arrange
    with (
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_fetch_series,
        patch(
            "app.services.sonarr_service.fetch_sonarr_episodes", new_callable=AsyncMock
        ) as mock_fetch_episodes,
    ):
        mock_fetch_series.return_value = sonarr_series_basic
        mock_fetch_episodes.side_effect = [
            sonarr_episodes_basic if series_id == 1 else []
            for series_id in [s["id"] for s in sonarr_series_basic]
        ]

        mock_season = Mock(spec=Season, series_id=1, number=1)

        mock_session.scalar.side_effect = [
            None,
            None,
            None,  # Series 1: imdb, title/year, Media
            None,
            None,
            mock_season,
            None,  # Season + 2 Episodes
            None,
            None,
            None,  # Series 2: imdb, title/year, Media
        ]

        expected_series_count = len(sonarr_series_basic)  # 2
        expected_episodes_count = len(sonarr_episodes_basic)  # 2
        unique_seasons = 1  # только сезон 1
        expected_entities_count = (
            (expected_series_count * 2) + unique_seasons + expected_episodes_count
        )  # 7

        # Act
        result = await import_sonarr_series(mock_session)

        # Assert
        expected_result = SonarrImportResponse(
            new_series=expected_series_count,
            new_episodes=expected_episodes_count,
            updated_series=0,
            updated_episodes=0,
        )

        assert "error" not in expected_result
        assert result == expected_result

        assert mock_session.scalar.call_count == 10  # 3 + 4 + 3
        assert mock_session.add.call_count == expected_entities_count  # 7
        assert mock_session.flush.call_count >= expected_series_count + 1  # 2 + 1 = 3+
        mock_session.commit.assert_awaited_once()
        mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_import_sonarr_series_updates_existing(
    mock_session, sonarr_series_basic, sonarr_episodes_basic
):
    """Test service updates existing Series and Episode entities."""
    # Arrange
    existing_series = Mock(
        spec=Series, sonarr_id=1, imdb_id="tt1234567", rating_value=7.0, year=2020
    )
    existing_episode = Mock(
        spec=Episode,
        sonarr_id=101,
        number=1,
        title="Old Title",
        overview="Old overview",
        air_date=None,
    )

    mock_session.scalar.side_effect = [
        existing_series,  # Series по imdb_id
        None,  # Season
        existing_episode,  # Episode
    ]

    with (
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_fetch_series,
        patch(
            "app.services.sonarr_service.fetch_sonarr_episodes", new_callable=AsyncMock
        ) as mock_fetch_episodes,
    ):
        mock_fetch_series.return_value = sonarr_series_basic[:1]  # Только одна серия
        mock_fetch_episodes.return_value = sonarr_episodes_basic[:1]  # Только один эпизод

        # Act
        result = await import_sonarr_series(mock_session)

        # Assert
        assert isinstance(result, SonarrImportResponse)
        exp_result = SonarrImportResponse(
            new_series=0, updated_series=1, new_episodes=0, updated_episodes=1, error=None
        )

        assert result == exp_result

        assert existing_series.sonarr_id == sonarr_series_basic[0]["id"]  # sonarr_id не изменился
        assert existing_episode.title == sonarr_episodes_basic[0]["title"]  # Обновление title
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_import_sonarr_series_real_data(mock_session, sonarr_series_from_json):
    """Test service with real Sonarr data from serials.json."""
    # Arrange
    with (
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_fetch_series,
        patch(
            "app.services.sonarr_service.fetch_sonarr_episodes", new_callable=AsyncMock
        ) as mock_fetch_episodes,
    ):
        mock_fetch_series.return_value = sonarr_series_from_json
        mock_fetch_episodes.return_value = []  # Упростим, без эпизодов
        mock_session.scalar.side_effect = [None, None, None] * len(
            sonarr_series_from_json
        )  # Series, Media

        # Act
        result = await import_sonarr_series(mock_session)

        # Assert
        exp_result = SonarrImportResponse(
            new_series=3,
            updated_series=0,
            new_episodes=0,
            updated_episodes=0,
            error=None,
        )

        assert result == exp_result

        assert mock_session.add.call_count == len(sonarr_series_from_json) * 2  # Media + Series
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_import_sonarr_series_failure_connection_timeout(mock_session):
    """Test service raises ClientError on connection timeout."""
    with patch(
        "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
    ) as mock_fetch_series:
        mock_fetch_series.side_effect = ClientError(
            code=SonarrErrorCode.NETWORK_ERROR, message="Failed to connect to Sonarr"
        )

        # Act & Assert
        with pytest.raises(ClientError) as exc_info:
            await import_sonarr_series(mock_session)

        assert exc_info.value.code == SonarrErrorCode.NETWORK_ERROR
        assert "connect" in exc_info.value.message.lower()

        mock_session.rollback.assert_not_called()
        mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_import_sonarr_series_skips_invalid(
    mock_session, sonarr_series_basic, sonarr_episodes_basic, mock_exists_result_false
):
    """Test service skips series and episodes with missing titles."""
    # Arrange
    invalid_series = sonarr_series_basic.copy()
    invalid_series[0]["title"] = None  # Серия без title
    invalid_episodes = sonarr_episodes_basic.copy()
    invalid_episodes[0]["title"] = None  # Эпизод без title

    with (
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_fetch_series,
        patch(
            "app.services.sonarr_service.fetch_sonarr_episodes", new_callable=AsyncMock
        ) as mock_fetch_episodes,
    ):
        mock_fetch_series.return_value = invalid_series
        mock_fetch_episodes.return_value = invalid_episodes
        mock_session.execute.return_value = mock_exists_result_false
        mock_session.scalar.return_value = None

        # Act
        result = await import_sonarr_series(mock_session)

        # Assert
        expected = SonarrImportResponse(
            new_series=1,
            updated_series=0,
            new_episodes=1,
            updated_episodes=0,
        )

        assert result == expected

        mock_session.commit.assert_awaited_once()
        mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_import_sonarr_series_invalid_date(
    mock_session, sonarr_series_invalid_data, sonarr_episodes_basic, mock_exists_result_false
):
    with (
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_fetch_series,
        patch(
            "app.services.sonarr_service.fetch_sonarr_episodes", new_callable=AsyncMock
        ) as mock_fetch_episodes,
    ):
        mock_fetch_series.return_value = sonarr_series_invalid_data
        mock_fetch_episodes.return_value = sonarr_episodes_basic
        mock_session.execute.return_value = mock_exists_result_false
        mock_session.scalar.return_value = None

        result = await import_sonarr_series(mock_session)

        expected = SonarrImportResponse(
            new_series=1,
            new_episodes=2,
            updated_series=0,
            updated_episodes=0,
        )

        assert result == expected

        mock_session.commit.assert_awaited_once()
        mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_import_sonarr_series_no_imdb_id(mock_session, sonarr_series_basic):
    """Test service handles series without imdb_id correctly."""
    # Arrange
    modified_series = sonarr_series_basic.copy()
    modified_series[0]["imdbId"] = None
    with (
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_fetch_series,
        patch(
            "app.services.sonarr_service.fetch_sonarr_episodes", new_callable=AsyncMock
        ) as mock_fetch_episodes,
    ):
        mock_fetch_series.return_value = modified_series
        mock_fetch_episodes.return_value = []
        mock_session.scalar.side_effect = [
            None,  # Series по imdb_id (первая серия)
            None,  # Series по title/year (первая серия)
            None,  # Media (первая серия)
            None,  # Series по imdb_id (вторая серия)
            None,  # Series по title/year (вторая серия)
            None,  # Media (вторая серия)
        ]

        # Act
        result = await import_sonarr_series(mock_session)

        # Assert
        exp_result = SonarrImportResponse(
            new_series=2, updated_series=0, new_episodes=0, updated_episodes=0
        )
        assert result == exp_result

        assert mock_session.add.call_count == 4  # Media + Series for each series
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_import_sonarr_series_invalid_episode_date(
    mock_session, sonarr_series_basic, sonarr_episodes_basic
):
    """Test service handles episodes with invalid airDateUtc."""
    # Arrange
    modified_episodes = sonarr_episodes_basic.copy()
    modified_episodes[0]["airDateUtc"] = "invalid_date"
    with (
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_fetch_series,
        patch(
            "app.services.sonarr_service.fetch_sonarr_episodes", new_callable=AsyncMock
        ) as mock_fetch_episodes,
    ):
        mock_fetch_series.return_value = sonarr_series_basic[:1]
        mock_fetch_episodes.return_value = modified_episodes
        mock_session.scalar.side_effect = [
            None,  # Series по imdb_id
            None,  # Series по title/year
            None,  # Media
            None,  # Season для первого эпизода
            None,  # Episode для первого эпизода
            None,  # Season для второго эпизода
            None,  # Episode для второго эпизода
        ]

        # Act
        result = await import_sonarr_series(mock_session)

        # Assert
        exp_result = SonarrImportResponse(
            new_series=1, new_episodes=2, updated_episodes=0, updated_series=0
        )

        assert result == exp_result

        mock_session.commit.assert_called_once()
        assert mock_session.add.call_count == 6  # Media, Series, two Seasons, two Episodes


@pytest.mark.asyncio
async def test_import_sonarr_series_update_episode(
    mock_session, sonarr_series_basic, sonarr_episodes_basic
):
    """Test updating an existing episode in import_sonarr_series."""
    with (
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_fetch_series,
        patch(
            "app.services.sonarr_service.fetch_sonarr_episodes", new_callable=AsyncMock
        ) as mock_fetch_episodes,
        patch("app.client.sonarr_client.SONARR_API_KEY", "test_key"),  # Патчим SONARR_API_KEY
    ):
        mock_fetch_series.return_value = sonarr_series_basic[:1]
        mock_fetch_episodes.return_value = sonarr_episodes_basic
        existing_episode = Episode(
            sonarr_id=sonarr_episodes_basic[0]["id"],
            title="Old title",
            season_id=1,
            number=1,
        )
        mock_session.scalar.side_effect = [
            None,  # Series по imdb_id
            None,  # Series по title/year
            None,  # Media
            None,  # Season
            existing_episode,  # Episode (существует)
            None,  # Season (для второго эпизода)
            None,  # Episode
        ]

        # Act
        result = await import_sonarr_series(mock_session)

        exp_result = SonarrImportResponse(
            new_series=1, new_episodes=1, updated_series=0, updated_episodes=1
        )
        # Assert
        assert result == exp_result

        mock_session.commit.assert_called_once()
        assert (
            mock_session.add.call_count >= 3
        )  # Media, Series, Season, Episode (для второго эпизода)
