from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.schemas.sonarr import SonarrImportResponse


@pytest.mark.asyncio
async def test_import_sonarr_success(
    async_client, mock_session, sonarr_series_basic, sonarr_episodes_basic, mock_exists_result_false
):
    """Test Sonarr import endpoint returns success response."""
    with (
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_fetch_series,
        patch(
            "app.services.sonarr_service.fetch_sonarr_episodes", new_callable=AsyncMock
        ) as mock_fetch_episodes,
        patch(
            "app.services.sonarr_service._find_series_by_sonarr_id", new_callable=AsyncMock
        ) as mock_find_sonarr,
        patch(
            "app.services.series_utils.find_series_by_external_ids", new_callable=AsyncMock
        ) as mock_find_external,
        patch(
            "app.services.sonarr_service._create_new_series", new_callable=AsyncMock
        ) as mock_create_series,
    ):
        modified_series = []
        for series in sonarr_series_basic:
            series_copy = series.copy()
            series_copy["seasons"] = [{"seasonNumber": 1}]
            series_copy["tmdbId"] = 12345 if series["id"] == 1 else 67890
            series_copy["imdbId"] = "tt1234567" if series["id"] == 1 else "tt7654321"
            modified_series.append(series_copy)

        mock_fetch_series.return_value = modified_series

        mock_fetch_episodes.side_effect = [
            sonarr_episodes_basic if series_id == 1 else []
            for series_id in [s["id"] for s in modified_series]
        ]

        mock_find_sonarr.return_value = None
        mock_find_external.return_value = None

        mock_series_list = []
        for i, series_data in enumerate(modified_series):
            mock_series = MagicMock()
            mock_series.id = i + 1
            mock_media = MagicMock()
            mock_media.title = series_data["title"]
            mock_series.media = mock_media
            mock_series_list.append(mock_series)

        mock_create_series.side_effect = mock_series_list

        mock_session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=None), scalars=Mock(return_value=[])
        )

        response = await async_client.post("/api/v1/sonarr/import")

        assert response.status_code == 200

        exp_resp = SonarrImportResponse(
            new_series=len(modified_series),
            updated_series=0,
            new_episodes=len(sonarr_episodes_basic),
            updated_episodes=0,
        ).model_dump(mode="json", exclude_none=True)
        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_import_sonarr_update_existing_series(
    async_client, mock_session, sonarr_episodes_basic
):
    """Test updating existing series with new data from Sonarr."""

    # Create mock existing series with tvdb_id that matches first test series
    existing_series = MagicMock()
    existing_series.sonarr_id = None
    existing_series.tvdb_id = "12345"  # Matches tvdbId of first series
    existing_series.imdb_id = None
    existing_series.media.title = "Old Title"
    existing_series.poster_url = None
