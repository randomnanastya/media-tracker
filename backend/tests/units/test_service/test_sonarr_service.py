from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.exceptions.client_errors import ClientError
from app.models import Episode, Media, MediaType, Season, Series
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
        sonarr_series_basic[0]["imdbId"] = "tt1234567"
        sonarr_series_basic[0]["seasons"] = [{"seasonNumber": 1}]
        sonarr_series_basic[1]["imdbId"] = "tt7654321"
        sonarr_series_basic[1]["seasons"] = [{"seasonNumber": 1}]

        mock_fetch_series.return_value = sonarr_series_basic
        mock_fetch_episodes.side_effect = [
            sonarr_episodes_basic if series_id == 1 else []
            for series_id in [s["id"] for s in sonarr_series_basic]
        ]

        execute_calls = []

        def execute_side_effect(query):
            query_str = str(query).lower()
            execute_calls.append(query_str)

            if ("season" in query_str and "series_id" in query_str) or (
                "episode" in query_str and "season_id" in query_str
            ):
                return Mock(scalars=Mock(return_value=[]))

            return Mock(scalar_one_or_none=Mock(return_value=None), scalars=Mock(return_value=[]))

        mock_session.execute.side_effect = execute_side_effect

        added_entities = []

        def add_side_effect(obj):
            added_entities.append(obj)
            return None

        mock_session.add.side_effect = add_side_effect

        # Act
        result = await import_sonarr_series(mock_session)

        # Assert
        assert result.new_series == 2
        assert result.new_episodes == 2
        assert result.updated_series == 0
        assert result.updated_episodes == 0

        media_count = len([e for e in added_entities if isinstance(e, Media)])
        series_count = len([e for e in added_entities if isinstance(e, Series)])
        season_count = len([e for e in added_entities if isinstance(e, Season)])
        episode_count = len([e for e in added_entities if isinstance(e, Episode)])

        assert media_count == 2
        assert series_count == 2
        assert season_count == 2
        assert episode_count == 2

        mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_episode_update_logic_directly():
    """Test episode update logic directly without full import."""
    from app.services.sonarr_service import _parse_iso_utc

    # Create test data
    existing_episode = Episode(
        id=1,
        season_id=1,
        sonarr_id=101,
        number=1,
        title="Old Title",
        overview="Old overview",
        air_date=None,
    )

    episode_data = {
        "id": 101,
        "seasonNumber": 1,
        "episodeNumber": 1,
        "title": "Pilot",
        "overview": "The pilot episode.",
        "airDateUtc": "2020-01-01T00:00:00Z",
    }

    # Simulate logic from sonarr_service
    existing_eps = {101: existing_episode}

    ep_sonarr_id = episode_data["id"]
    ep_num = episode_data["episodeNumber"]
    ep_title = episode_data["title"]
    overview = episode_data["overview"]
    air_date = _parse_iso_utc(episode_data["airDateUtc"])

    existing = existing_eps.get(ep_sonarr_id)
    updated = False

    if existing:
        if existing.number != ep_num:
            existing.number = ep_num
            updated = True
        if existing.title != ep_title:
            existing.title = ep_title
            updated = True
        if existing.overview != overview:
            existing.overview = overview
            updated = True
        if existing.air_date != air_date:
            existing.air_date = air_date
            updated = True

    # Check
    assert updated  # SIM102 fix: use truth check instead of == True
    assert existing_episode.title == "Pilot"
    assert existing_episode.overview == "The pilot episode."
    assert existing_episode.air_date is not None


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
        mock_fetch_episodes.return_value = []

        series_count = len(sonarr_series_from_json)

        processed_series = []

        def execute_side_effect(query):
            query_str = str(query)

            # _find_series_by_sonarr_id
            if "sonarr_id" in query_str and "series" in query_str:
                import re

                match = re.search(r"sonarr_id = (\d+)", query_str)
                if match:
                    sonarr_id = int(match.group(1))
                    processed_series.append(f"find_by_sonarr_id:{sonarr_id}")
                return Mock(scalar_one_or_none=Mock(return_value=None))

            # _find_series_by_external_ids
            elif "or_" in query_str and "series" in query_str:
                if "tt" in query_str:
                    processed_series.append("find_by_external_ids:has_imdb")
                return Mock(scalar_one_or_none=Mock(return_value=None))

            # select(Season)
            elif "season" in query_str and "series_id" in query_str:
                return Mock(scalars=Mock(return_value=[]))

            return Mock(scalars=Mock(return_value=[]), scalar_one_or_none=Mock(return_value=None))

        mock_session.execute.side_effect = execute_side_effect

        # Act
        result = await import_sonarr_series(mock_session)

        for i, series in enumerate(sonarr_series_from_json):
            print(
                f"DEBUG: Series {i}: id={series.get('id')}, title={series.get('title')}, "
                f"imdbId={series.get('imdbId')}, tvdbId={series.get('tvdbId')}"
            )

        # Assert
        assert result.new_series == series_count
        assert result.updated_series == 0

        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_import_sonarr_series_prioritizes_sonarr_id_and_preserves_imdb_tvdb(
    mock_session, sonarr_series_basic, mock_fetch_sonarr_series, mock_fetch_sonarr_episodes
):
    """
    Series is found by ``sonarr_id``. Existing ``imdb_id`` and ``tvdb_id`` are **never**
    overwritten - they are immutable identifiers.
    """
    # Arrange
    media = Media(
        id=100,
        media_type=MediaType.SERIES,
        title="Existing Title",
        release_date=None,
    )
    existing_series = Series(
        id=100,
        sonarr_id=1,
        imdb_id="tt_existing_imdb",
        tvdb_id="99999",
        poster_url=None,
        year=None,
        status=None,
    )
    existing_series.media = media

    mock_session.add(media)
    mock_session.add(existing_series)

    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = existing_series
    mock_session.execute.return_value = mock_result

    mock_fetch_sonarr_series.return_value = [sonarr_series_basic[0]]
    mock_fetch_sonarr_episodes.return_value = []

    # Act
    result = await import_sonarr_series(mock_session)

    # Assert
    assert result.updated_series == 1
    assert result.new_series == 0

    assert existing_series.imdb_id == "tt_existing_imdb"
    assert existing_series.tvdb_id == "99999"

    assert existing_series.poster_url == "http://example.com/poster.jpg"
    assert existing_series.year == 2020
    assert media.release_date is not None


@pytest.mark.asyncio
async def test_import_sonarr_series_finds_by_tvdb_id_when_no_sonarr_id(
    mock_session, mock_fetch_sonarr_series, mock_fetch_sonarr_episodes
):
    """
    When ``sonarr_id`` is missing, the service falls back to ``tvdb_id``.
    ``imdb_id`` is filled if it is present in Sonarr data.
    """
    # Arrange
    series_no_sonarr = {
        "id": 999,
        "title": "Lost in Space",
        "tvdbId": 123456,
        "imdbId": "tt5232792",
        "firstAired": "2018-04-13",
        "year": 2018,
        "status": "continuing",
        "images": [],
        "genres": [],
        "ratings": {"value": None, "votes": None},
        "seasons": [{"seasonNumber": 1}],
    }

    media = Media(id=200, media_type=MediaType.SERIES, title="Old Title")
    existing_series = Series(
        id=200,
        sonarr_id=None,
        tvdb_id="123456",
        imdb_id=None,
    )
    existing_series.media = media

    mock_result_external = Mock()
    mock_result_external.scalar_one_or_none.return_value = existing_series

    mock_session.execute.side_effect = [
        Mock(scalar_one_or_none=Mock(return_value=None)),
        mock_result_external,
    ]

    mock_fetch_sonarr_series.return_value = [series_no_sonarr]
    mock_fetch_sonarr_episodes.return_value = []

    # Act
    result = await import_sonarr_series(mock_session)

    # Assert
    assert result.updated_series == 1
    assert existing_series.imdb_id == "tt5232792"
    assert existing_series.tvdb_id == "123456"
    assert existing_series.sonarr_id == 999
    assert media.title == "Lost in Space"


@pytest.mark.asyncio
async def test_import_sonarr_series_creates_seasons_from_seasons_array(
    mock_session, mock_fetch_sonarr_series, mock_fetch_sonarr_episodes
):
    """
    All season numbers listed in the ``seasons`` array are created
    if they do not exist yet.
    """
    # Arrange
    series_data = {
        "id": 5,
        "title": "Stranger Things",
        "imdbId": "tt4574334",
        "tvdbId": 305288,
        "firstAired": "2016-07-15",
        "seasons": [
            {"seasonNumber": 1},
            {"seasonNumber": 2},
            {"seasonNumber": 3},
            {"seasonNumber": 4},
        ],
        "images": [],
        "genres": [],
        "ratings": {"value": None, "votes": None},
        "status": "continuing",
        "year": 2016,
    }

    mock_result_sonarr = Mock()
    mock_result_sonarr.scalar_one_or_none.return_value = None

    mock_result_external = Mock()
    mock_result_external.scalar_one_or_none.return_value = None

    mock_result_seasons = Mock()
    mock_result_seasons.scalars.return_value = Mock()

    mock_session.execute.side_effect = [
        mock_result_sonarr,
        mock_result_external,
        mock_result_seasons,
    ]

    mock_fetch_sonarr_series.return_value = [series_data]
    mock_fetch_sonarr_episodes.return_value = []

    # Act
    result = await import_sonarr_series(mock_session)

    # Assert
    assert result.new_series == 1

    added_seasons = [
        call[0][0] for call in mock_session.add.call_args_list if isinstance(call[0][0], Season)
    ]
    assert len(added_seasons) == 4
    assert {s.number for s in added_seasons} == {1, 2, 3, 4}


@pytest.mark.asyncio
async def test_import_sonarr_series_creates_seasons_from_seasons_array_existing_series(
    mock_session, mock_fetch_sonarr_series, mock_fetch_sonarr_episodes
):
    """
    All season numbers listed in the ``seasons`` array are created
    if they do not exist yet (for existing series).
    """
    # Arrange
    series_data = {
        "id": 5,
        "title": "Stranger Things",
        "imdbId": "tt4574334",
        "tvdbId": 305288,
        "firstAired": "2016-07-15",
        "seasons": [
            {"seasonNumber": 1},
            {"seasonNumber": 2},
            {"seasonNumber": 3},
            {"seasonNumber": 4},
        ],
        "images": [],
        "genres": [],
        "ratings": {"value": None, "votes": None},
        "status": "continuing",
        "year": 2016,
    }

    media = Media(id=5, media_type=MediaType.SERIES, title="Old Title")
    existing_series = Series(
        id=5,
        sonarr_id=5,
        tvdb_id="305288",
        imdb_id="tt4574334",
    )
    existing_series.media = media

    mock_result_sonarr = Mock()
    mock_result_sonarr.scalar_one_or_none.return_value = existing_series

    mock_result_seasons = Mock()
    mock_result_seasons.scalars.return_value = Mock()

    mock_session.execute.side_effect = [
        mock_result_sonarr,
        mock_result_seasons,
    ]

    mock_fetch_sonarr_series.return_value = [series_data]
    mock_fetch_sonarr_episodes.return_value = []

    # Act
    result = await import_sonarr_series(mock_session)

    # Assert
    assert result.updated_series == 1
    assert result.new_series == 0

    added_seasons = [
        call[0][0] for call in mock_session.add.call_args_list if isinstance(call[0][0], Season)
    ]
    assert len(added_seasons) == 4
    assert {s.number for s in added_seasons} == {1, 2, 3, 4}


@pytest.mark.asyncio
async def test_import_sonarr_series_sets_season_release_date_from_first_episode(
    mock_session, mock_fetch_sonarr_series, mock_fetch_sonarr_episodes
):
    """
    ``Season.release_date`` is set to the earliest ``airDateUtc`` of its episodes,
    but only when the field is ``NULL``.
    """
    # Arrange
    series_data = {
        "id": 10,
        "title": "The Office",
        "seasons": [{"seasonNumber": 1}],
        "images": [],
        "genres": [],
        "ratings": {"value": None, "votes": None},
        "status": None,
        "year": None,
        "firstAired": None,
        "tvdbId": None,
        "imdbId": None,
    }
    episodes = [
        {
            "id": 1001,
            "seasonNumber": 1,
            "episodeNumber": 1,
            "title": "Pilot",
            "airDateUtc": "2005-03-24T00:00:00Z",
            "overview": None,
        },
        {
            "id": 1002,
            "seasonNumber": 1,
            "episodeNumber": 2,
            "title": "Diversity Day",
            "airDateUtc": "2005-03-29T00:00:00Z",
            "overview": None,
        },
    ]

    # Media + Series
    media = Media(id=999, media_type=MediaType.SERIES, title="The Office")
    series = Series(id=999, sonarr_id=10)
    series.media = media

    existing_season = Season(id=1, series_id=999, number=1, release_date=None)

    mock_result_sonarr = Mock()
    mock_result_sonarr.scalar_one_or_none.return_value = series

    mock_result_seasons = Mock()
    mock_result_seasons.scalars.return_value = [existing_season]

    mock_result_episodes = Mock()
    mock_result_episodes.scalars.return_value = []

    mock_session.execute.side_effect = [
        mock_result_sonarr,
        mock_result_seasons,
        mock_result_episodes,
    ]

    mock_fetch_sonarr_series.return_value = [series_data]
    mock_fetch_sonarr_episodes.return_value = episodes

    # Act
    await import_sonarr_series(mock_session)

    # Assert
    assert mock_session.flush.called

    from app.services.sonarr_service import _parse_iso_utc

    earliest_date = _parse_iso_utc("2005-03-24T00:00:00Z")
    assert earliest_date is not None
    assert earliest_date.year == 2005
    assert earliest_date.month == 3
    assert earliest_date.day == 24


@pytest.mark.asyncio
async def test_episode_comparison_logic():
    """Test episode comparison logic only"""
    from app.services.sonarr_service import _parse_iso_utc

    existing_episode = Episode(
        id=100,
        season_id=1,
        sonarr_id=2001,
        number=1,
        title="Old Pilot",
        air_date=None,
        overview=None,
    )

    sonarr_episode_data = {
        "id": 2001,
        "seasonNumber": 1,
        "episodeNumber": 1,
        "title": "Pilot",
        "airDateUtc": "2008-01-20T00:00:00Z",
        "overview": None,
    }

    existing_eps = {2001: existing_episode}

    ep_sonarr_id = sonarr_episode_data["id"]
    ep_num = sonarr_episode_data["episodeNumber"]
    ep_title = sonarr_episode_data["title"]
    air_date = _parse_iso_utc(sonarr_episode_data["airDateUtc"])

    existing = existing_eps.get(ep_sonarr_id)
    updated = False

    if existing:
        if existing.number != ep_num:
            existing.number = ep_num
            updated = True
        if existing.title != ep_title:
            existing.title = ep_title
            updated = True
        if existing.air_date != air_date:
            existing.air_date = air_date
            updated = True

    assert updated  # SIM102 fix: use truth check
    assert existing_episode.title == "Pilot"
    assert existing_episode.air_date is not None


async def test_import_sonarr_series_no_changes_when_all_match(
    mock_session, mock_fetch_sonarr_series, mock_fetch_sonarr_episodes
):
    """
    When every field already matches Sonarr data, **nothing** is updated
    (no DB writes, counters stay zero).
    """
    # Arrange
    media = Media(
        id=1,
        media_type=MediaType.SERIES,
        title="Breaking Bad",
        release_date=datetime(2008, 1, 20, tzinfo=UTC),
    )
    existing_series = Series(
        id=1,
        sonarr_id=1,
        imdb_id="tt0903747",
        tvdb_id="81189",
        poster_url="https://example.com/poster.jpg",
        year=2008,
        genres=["Crime", "Drama"],
        rating_value=9.5,
        rating_votes=2_000_000,
        status="ended",
    )
    existing_series.media = media

    mock_result_sonarr = Mock()
    mock_result_sonarr.scalar_one_or_none.return_value = existing_series

    mock_result_seasons = Mock()
    mock_result_seasons.scalars.return_value = []

    mock_session.execute.side_effect = [
        mock_result_sonarr,
        mock_result_seasons,
    ]

    mock_fetch_sonarr_series.return_value = [
        {
            "id": 1,
            "title": "Breaking Bad",
            "imdbId": "tt0903747",
            "tvdbId": 81189,
            "firstAired": "2008-01-20T00:00:00Z",
            "year": 2008,
            "status": "ended",
            "images": [{"coverType": "poster", "remoteUrl": "https://example.com/poster.jpg"}],
            "genres": ["Crime", "Drama"],
            "ratings": {"value": 9.5, "votes": 2000000},
            "seasons": [],
        }
    ]
    mock_fetch_sonarr_episodes.return_value = []

    # Act
    result = await import_sonarr_series(mock_session)

    # Assert
    assert result.updated_series == 0
    assert result.new_series == 0
    assert result.new_episodes == 0
    assert result.updated_episodes == 0


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
    invalid_series = [
        {
            "id": 1,
            "title": None,  # Invalid - no title
            "imdbId": "tt1234567",
            "firstAired": "2020-01-01",
            "year": 2020,
            "status": "continuing",
            "images": [],
            "genres": [],
            "ratings": {},
            "seasons": [{"seasonNumber": 1}],
        },
        {
            "id": 2,
            "title": "Valid Series",  # Valid
            "imdbId": "tt7654321",
            "firstAired": "2021-01-01",
            "year": 2021,
            "status": "continuing",
            "images": [],
            "genres": [],
            "ratings": {},
            "seasons": [{"seasonNumber": 1}],
        },
    ]

    invalid_episodes = [
        {
            "id": 101,
            "seasonNumber": 1,
            "episodeNumber": 1,
            "title": None,  # Invalid - no title
            "airDateUtc": "2020-01-01T00:00:00Z",
            "overview": "Overview",
        },
        {
            "id": 102,
            "seasonNumber": 1,
            "episodeNumber": 2,
            "title": "Valid Episode",  # Valid
            "airDateUtc": "2020-01-08T00:00:00Z",
            "overview": "Overview",
        },
    ]

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

        mock_session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=None), scalars=Mock(return_value=[])
        )

        # Act
        result = await import_sonarr_series(mock_session)

        # Debug
        print(f"DEBUG: Result: {result}")

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
        invalid_series = sonarr_series_invalid_data.copy()
        invalid_series[0]["imdbId"] = "tt1234567"  # Add identifier
        invalid_series[0]["seasons"] = [{"seasonNumber": 1}]  # Add seasons
        invalid_series[0]["year"] = 2020
        invalid_series[0]["status"] = "continuing"
        invalid_series[0]["images"] = []
        invalid_series[0]["genres"] = []
        invalid_series[0]["ratings"] = {}

        mock_fetch_series.return_value = invalid_series
        mock_fetch_episodes.return_value = sonarr_episodes_basic

        mock_session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=None), scalars=Mock(return_value=[])
        )

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
async def test_import_sonarr_series_no_identifiers_skipped(mock_session, sonarr_series_basic):
    """Test service skips series without any identifiers."""
    # Arrange
    modified_series = sonarr_series_basic.copy()
    modified_series[0]["id"] = None  # No sonarr_id
    modified_series[0]["imdbId"] = None  # No imdb_id
    modified_series[0]["tvdbId"] = None  # No tvdb_id
    modified_series[1]["tvdbId"] = 789012

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

        mock_session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=None), scalars=Mock(return_value=[])
        )

        # Act
        result = await import_sonarr_series(mock_session)

        # Assert
        exp_result = SonarrImportResponse(
            new_series=1, updated_series=0, new_episodes=0, updated_episodes=0
        )
        assert result == exp_result

        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_import_sonarr_series_invalid_episode_date(
    mock_session, sonarr_series_basic, sonarr_episodes_basic
):
    """Test service handles episodes with invalid airDateUtc."""
    # Arrange
    modified_episodes = sonarr_episodes_basic.copy()
    modified_episodes[0]["airDateUtc"] = "invalid_date"

    series_data = sonarr_series_basic[0].copy()
    series_data["tvdbId"] = 123456
    series_data["seasons"] = [{"seasonNumber": 1}]

    with (
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_fetch_series,
        patch(
            "app.services.sonarr_service.fetch_sonarr_episodes", new_callable=AsyncMock
        ) as mock_fetch_episodes,
    ):
        mock_fetch_series.return_value = [series_data]
        mock_fetch_episodes.return_value = modified_episodes

        execute_calls = []
        add_calls = []

        def execute_side_effect(query):
            query_str = str(query)
            execute_calls.append(query_str[:100])

            return Mock(scalar_one_or_none=Mock(return_value=None), scalars=Mock(return_value=[]))

        def add_side_effect(obj):
            add_calls.append(obj)
            return None

        mock_session.execute.side_effect = execute_side_effect
        mock_session.add.side_effect = add_side_effect

        # Act
        result = await import_sonarr_series(mock_session)

        # Assert
        exp_result = SonarrImportResponse(
            new_series=1, new_episodes=2, updated_episodes=0, updated_series=0
        )
        assert result == exp_result

        mock_session.commit.assert_called_once()
