from datetime import datetime
from unittest.mock import Mock

import pytest

from app.services.radarr_service import import_radarr_movies


def count_movies_without_id(movies):
    """Helper to count movies without Radarr ID"""
    return sum(1 for movie in movies if "id" not in movie)


def count_valid_movies(movies):
    valid_movies = []
    for m in movies:
        if not m.get("id"):
            continue
        date_str = m.get("inCinemas")
        if date_str:
            try:
                datetime.fromisoformat(date_str)
            except ValueError:
                continue  # skip invalid date
        valid_movies.append(m)
    return len(valid_movies)


def count_invalid_movies(movies):
    """Return number of movies that would be skipped (no id or invalid date)."""
    invalid_count = 0
    for m in movies:
        if not m.get("id"):
            invalid_count += 1
            continue
        date_str = m.get("inCinemas")
        if date_str:
            try:
                datetime.fromisoformat(date_str)
            except ValueError:
                invalid_count += 1
                continue
    return invalid_count


def calculate_expected_entities_count(movies_count):
    """Calculate expected number of entities created (Media + Movie per film)"""
    return movies_count * 2


@pytest.mark.asyncio
async def test_import_radarr_movies_creates_both_entities(
    mock_session, radarr_movies_basic, mock_fetch_radarr_movies, mock_exists_result_false
):
    """Test service creates both Media and Movie entities for each movie"""
    # Arrange
    mock_fetch_radarr_movies.return_value = radarr_movies_basic

    mock_exists_result_false.scalar.return_value = False

    mock_find_result = Mock()
    mock_find_result.scalar_one_or_none.return_value = None

    execute_calls = []
    for _ in radarr_movies_basic:
        execute_calls.extend([mock_exists_result_false, mock_find_result])

    mock_session.execute.side_effect = execute_calls

    expected_movies_count = len(radarr_movies_basic)

    # Act
    result = await import_radarr_movies(mock_session)

    assert (
        result.imported_count == expected_movies_count
    ), f"Expected to import {expected_movies_count} movies, but got {result}"

    expected_execute_calls = 2 * expected_movies_count
    assert (
        mock_session.execute.call_count == expected_execute_calls
    ), f"Expected {expected_execute_calls} execute calls, but got {mock_session.execute.call_count}"

    expected_add_calls = 2 * expected_movies_count
    assert (
        mock_session.add.call_count == expected_add_calls
    ), f"Expected {expected_add_calls} add calls, but got {mock_session.add.call_count}"

    assert (
        mock_session.flush.call_count == expected_movies_count
    ), f"Expected {expected_movies_count} flush calls, but got {mock_session.flush.call_count}"

    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_import_radarr_movie_without_radarr_id_updates_by_tmdb(
    mock_session, mock_fetch_radarr_movies, existing_movie_by_tmdb_in_db
):
    """Фильм без radarr_id, но с tmdb_id → находит и обновляет"""
    # Arrange
    mock_fetch_radarr_movies.return_value = [
        {
            "id": None,
            "title": "Inception",
            "tmdbId": 27205,
            "imdbId": "tt1375666",
            "inCinemas": "2010-07-16T00:00:00Z",
        }
    ]

    mock_exists_result = Mock()
    mock_exists_result.scalar.return_value = False
    mock_session.execute.return_value = mock_exists_result

    mock_find_result = Mock()
    mock_find_result.scalar_one_or_none.return_value = existing_movie_by_tmdb_in_db
    mock_session.execute.return_value = mock_find_result

    # Act
    result = await import_radarr_movies(mock_session)

    # Assert
    assert result.imported_count == 0
    assert result.updated_count == 1

    assert existing_movie_by_tmdb_in_db.imdb_id == "tt1375666"
    assert existing_movie_by_tmdb_in_db.media.release_date is not None
    assert existing_movie_by_tmdb_in_db.media.release_date.year == 2010


@pytest.mark.asyncio
async def test_import_radarr_movie_without_radarr_id_updates_by_imdb(
    mock_session, mock_fetch_radarr_movies, existing_movie_by_imdb_in_db
):
    """Фильм без radarr_id, но с imdb_id → находит и обновляет"""
    # Arrange
    mock_fetch_radarr_movies.return_value = [
        {
            "id": None,
            "title": "The Matrix",
            "tmdbId": 603,
            "imdbId": "tt0133093",
            "inCinemas": "1999-03-31",
        }
    ]

    mock_find_result = Mock()
    mock_find_result.scalar_one_or_none.return_value = existing_movie_by_imdb_in_db

    mock_session.execute.return_value = mock_find_result

    # Act
    result = await import_radarr_movies(mock_session)

    # Assert
    assert result.imported_count == 0
    assert result.updated_count == 1

    assert existing_movie_by_imdb_in_db.tmdb_id == "603"
    assert existing_movie_by_imdb_in_db.media.release_date is not None


@pytest.mark.asyncio
async def test_import_radarr_movie_with_radarr_id_updates_existing_by_tmdb(
    mock_session, mock_fetch_radarr_movies, existing_movie_by_tmdb_in_db
):
    """Фильм с radarr_id, но уже есть по tmdb → обновляет radarr_id"""
    # Arrange
    mock_fetch_radarr_movies.return_value = [
        {
            "id": 123,
            "title": "Inception",
            "tmdbId": 27205,
            "imdbId": "tt1375666",
            "inCinemas": "2010-07-16",
        }
    ]

    mock_exists_result = Mock()
    mock_exists_result.scalar.return_value = False

    mock_find_result = Mock()
    mock_find_result.scalar_one_or_none.return_value = existing_movie_by_tmdb_in_db

    mock_session.execute.side_effect = [
        mock_exists_result,
        mock_find_result,
    ]

    # Act
    result = await import_radarr_movies(mock_session)

    # Assert
    assert result.imported_count == 0
    assert result.updated_count == 1

    assert existing_movie_by_tmdb_in_db.radarr_id == 123
    assert existing_movie_by_tmdb_in_db.imdb_id == "tt1375666"


@pytest.mark.asyncio
async def test_import_radarr_movie_without_ids_skips_creation(
    mock_session, mock_fetch_radarr_movies, mock_exists_result_false
):
    """Фильм без radarr_id и без tmdb/imdb → пропускает создание"""
    # Arrange
    mock_fetch_radarr_movies.return_value = [
        {"id": None, "title": "Unknown Movie", "tmdbId": None, "imdbId": None, "inCinemas": None}
    ]

    mock_find_result = Mock()
    mock_find_result.scalar_one_or_none.return_value = None

    mock_session.execute.return_value = mock_find_result

    # Act
    result = await import_radarr_movies(mock_session)

    # Assert
    assert result.imported_count == 0
    assert result.updated_count == 0
    assert mock_session.add.call_count == 0


@pytest.mark.asyncio
async def test_import_radarr_movie_without_radarr_id_already_complete_skips_update(
    mock_session, mock_fetch_radarr_movies, existing_movie_complete_in_db
):
    """Фильм без radarr_id, но в БД уже всё заполнено → пропускает"""
    # Arrange
    mock_fetch_radarr_movies.return_value = [
        {
            "id": None,
            "title": "Inception",
            "tmdbId": 27205,
            "imdbId": "tt1375666",
            "inCinemas": "2010-07-16",
        }
    ]

    mock_find_result = Mock()
    mock_find_result.scalar_one_or_none.return_value = existing_movie_complete_in_db
    mock_session.execute.return_value = mock_find_result

    # Act
    result = await import_radarr_movies(mock_session)

    # Assert
    assert result.imported_count == 0
    assert result.updated_count == 0


@pytest.mark.asyncio
async def test_import_radarr_movies_skips_existing_movies(
    mock_session, mock_fetch_radarr_movies, sample_movies_mixed, setup_mock_session_exists_check
):
    """Test service skips movies that already exist in database"""
    # Arrange
    mock_fetch_radarr_movies.return_value = sample_movies_mixed

    # First movie exists, second is new
    setup_mock_session_exists_check([True, False])

    expected_imported_count = 1
    expected_entities_count = calculate_expected_entities_count(expected_imported_count)

    # Act
    result = await import_radarr_movies(mock_session)

    # Assert
    assert (
        result.imported_count == expected_imported_count
    ), f"Expected to import {expected_imported_count} new movies, but got {result.imported_count}"

    assert (
        mock_session.add.call_count == expected_entities_count
    ), f"Expected {expected_entities_count} entities created, but got {mock_session.add.call_count}"

    assert (
        mock_session.flush.call_count == expected_imported_count
    ), f"Expected {expected_imported_count} flush calls, but got {mock_session.flush.call_count}"


@pytest.mark.asyncio
async def test_import_radarr_movies_handles_partial_insert_failure(
    mock_session, mock_fetch_radarr_movies, sample_movies_basic
):
    """Test service performs transaction rollback when flush fails during movie import"""
    # Arrange
    movies_with_tmdb = [
        {"id": 1, "title": "Movie 1", "inCinemas": "2023-01-01T00:00:00Z", "tmdbId": 1001},
        {"id": 2, "title": "Movie 2", "inCinemas": "2023-02-01T00:00:00Z", "tmdbId": 1002},
    ]
    mock_fetch_radarr_movies.return_value = movies_with_tmdb

    mock_exists_1 = Mock()
    mock_exists_1.scalar.return_value = False

    mock_exists_2 = Mock()
    mock_exists_2.scalar.return_value = False

    mock_find_1 = Mock()
    mock_find_1.scalar_one_or_none.return_value = None

    mock_find_2 = Mock()
    mock_find_2.scalar_one_or_none.return_value = None

    execute_call_count = 0

    async def mock_execute(query):
        nonlocal execute_call_count
        execute_call_count += 1

        mock_map = {
            1: mock_exists_1,
            2: mock_find_1,
            3: mock_exists_2,
            4: mock_find_2,
        }

        return mock_map.get(execute_call_count, Mock(scalar_one_or_none=lambda: None))

    mock_session.execute.side_effect = mock_execute

    flush_call_count = 0

    async def mock_flush():
        nonlocal flush_call_count
        flush_call_count += 1
        if flush_call_count == 2:
            raise Exception("Flush failed")

    mock_session.flush.side_effect = mock_flush

    # Act & Assert
    with pytest.raises(Exception, match="Flush failed"):
        await import_radarr_movies(mock_session)

    # Assert
    assert flush_call_count == 2, f"Expected 2 flush calls, got {flush_call_count}"
    assert execute_call_count == 4, f"Expected 4 execute calls, got {execute_call_count}"

    mock_session.rollback.assert_called_once()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_import_radarr_movies_handles_commit_failure(
    mock_session, mock_fetch_radarr_movies, mock_exists_result_false, sample_movies_basic
):
    """Test service handles commit failure"""
    # Arrange
    mock_fetch_radarr_movies.return_value = sample_movies_basic
    mock_session.execute.return_value = mock_exists_result_false

    # Simulate commit failure
    mock_session.commit.side_effect = Exception("Commit failed")

    expected_error_message = "Commit failed"

    # Act & Assert
    with pytest.raises(Exception, match=expected_error_message):
        await import_radarr_movies(mock_session)

    assert mock_session.rollback.call_count == 1, "Expected rollback after commit failure"


@pytest.mark.asyncio
async def test_import_radarr_movies_skips_movies_without_id(
    mock_session,
    radarr_movies_without_require_fields,
    mock_fetch_radarr_movies,
    mock_exists_result_false,
):
    """Test service skips movies without Radarr ID"""
    # Arrange
    mock_fetch_radarr_movies.return_value = radarr_movies_without_require_fields

    mock_exists_result_false.scalar.return_value = False

    mock_find_result = Mock()
    mock_find_result.scalar_one_or_none.return_value = None

    valid_movies = [m for m in radarr_movies_without_require_fields if m.get("id") is not None]
    expected_valid_count = len(valid_movies)
    expected_invalid_count = len(radarr_movies_without_require_fields) - expected_valid_count

    execute_calls = []
    for _ in valid_movies:
        execute_calls.extend([mock_exists_result_false, mock_find_result])

    mock_session.execute.side_effect = execute_calls

    # Act
    result = await import_radarr_movies(mock_session)

    # Assert
    assert (
        result.imported_count == expected_valid_count
    ), f"Expected to import {expected_valid_count} valid movies, but got {result.imported_count}"

    expected_execute_calls = 2 * expected_valid_count
    assert (
        mock_session.execute.call_count == expected_execute_calls
    ), f"Expected {expected_execute_calls} execute calls, but got {mock_session.execute.call_count}"

    total_movies = len(radarr_movies_without_require_fields)
    assert (
        total_movies == expected_valid_count + expected_invalid_count
    ), f"Movie count mismatch: {expected_valid_count} valid + {expected_invalid_count} invalid should equal {total_movies} total"
