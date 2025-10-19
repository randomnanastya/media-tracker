from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.models import Episode, Season, Series
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
            None,  # Series по imdb_id (серия 1)
            None,  # Series по title/year (серия 1)
            None,  # Media (серия 1)
            None,  # Season (серия 1, первый эпизод)
            None,  # Episode 1
            mock_season,  # Season (серия 1, второй эпизод)
            None,  # Episode 2
            None,  # Series по imdb_id (серия 2)
            None,  # Series по title/year (серия 2)
            None,  # Media (серия 2)
        ]

        expected_series_count = len(sonarr_series_basic)
        expected_episodes_count = len(sonarr_episodes_basic)
        expected_entities_count = calculate_expected_entities_count(
            expected_series_count, sonarr_episodes_basic
        )

        # Act
        result = await import_sonarr_series(mock_session)

        # Assert
        assert isinstance(result, SonarrImportResponse)
        expected_result = {
            "new_series": expected_series_count,
            "new_episodes": expected_episodes_count,
            "updated_series": 0,
            "updated_episodes": 0,
            "error": None,
        }
        assert result.model_dump() == expected_result

        assert mock_session.scalar.call_count >= expected_series_count * 2
        assert mock_session.add.call_count == expected_entities_count
        assert mock_session.flush.call_count >= expected_series_count + 1
        mock_session.commit.assert_called_once()
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
        expected_result = {
            "new_series": 0,
            "updated_series": 1,
            "new_episodes": 0,
            "updated_episodes": 1,
            "error": None,
        }

        assert result.model_dump() == expected_result

        assert existing_series.sonarr_id == sonarr_series_basic[0]["id"]  # sonarr_id не изменился
        assert existing_episode.title == sonarr_episodes_basic[0]["title"]  # Обновление title
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_import_sonarr_series_failure(mock_session):
    """Test service handles fetch failure correctly."""
    with patch(
        "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
    ) as mock_fetch_series:
        mock_fetch_series.side_effect = Exception("Connection timeout")

        # Act
        result = await import_sonarr_series(mock_session)

        # Assert
        assert isinstance(result, SonarrImportResponse)
        expected_result = {
            "new_series": 0,
            "updated_series": 0,
            "new_episodes": 0,
            "updated_episodes": 0,
            "error": {
                "code": "SONARR_FETCH_FAILED",
                "message": "Failed to fetch series: Connection timeout",
            },
        }

        assert result.model_dump() == expected_result

        mock_session.commit.assert_not_called()
        mock_session.rollback.assert_not_called()


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
        patch("app.core.logging.logger.warning") as mock_logger_warning,
    ):
        mock_fetch_series.return_value = invalid_series
        mock_fetch_episodes.return_value = invalid_episodes
        mock_session.execute.return_value = mock_exists_result_false
        mock_session.scalar.return_value = None

        # Act
        result = await import_sonarr_series(mock_session)

        # Assert
        assert isinstance(result, SonarrImportResponse)
        assert result.new_series == 1
        assert result.new_episodes == 1
        assert result.error is None
        mock_logger_warning.assert_called()
        mock_session.commit.assert_called_once()
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
        patch("app.core.logging.logger.error") as mock_logger_error,
    ):
        mock_fetch_series.return_value = sonarr_series_invalid_data
        mock_fetch_episodes.return_value = sonarr_episodes_basic
        mock_session.execute.return_value = mock_exists_result_false
        mock_session.scalar.return_value = None

        result = await import_sonarr_series(mock_session)

        assert result.new_series == 1
        mock_logger_error.assert_called_with(
            "Invalid firstAired date for series %s: %s", "Pilot", "invalid_date"
        )
