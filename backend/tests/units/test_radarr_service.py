import pytest

from app.services.radarr_service import import_radarr_movies


def count_movies_without_id(movies):
    """Helper to count movies without Radarr ID"""
    return sum(1 for movie in movies if "id" not in movie)


def count_valid_movies(movies):
    """Helper to count movies with Radarr ID"""
    return sum(1 for movie in movies if "id" in movie)


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
    mock_session.execute.return_value = mock_exists_result_false

    expected_movies_count = len(radarr_movies_basic)
    expected_entities_count = calculate_expected_entities_count(expected_movies_count)

    # Act
    imported_count = await import_radarr_movies(mock_session)

    # Assert
    assert (
        imported_count == expected_movies_count
    ), f"Expected to import {expected_movies_count} movies, but got {imported_count}"

    assert (
        mock_session.execute.call_count == expected_movies_count
    ), f"Expected {expected_movies_count} existence checks, but got {mock_session.execute.call_count}"

    assert (
        mock_session.add.call_count == expected_entities_count
    ), f"Expected {expected_entities_count} entities created, but got {mock_session.add.call_count}"

    assert (
        mock_session.flush.call_count == expected_movies_count
    ), f"Expected {expected_movies_count} flush calls, but got {mock_session.flush.call_count}"

    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_not_called()


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
    imported_count = await import_radarr_movies(mock_session)

    # Assert
    assert (
        imported_count == expected_imported_count
    ), f"Expected to import {expected_imported_count} new movies, but got {imported_count}"

    assert (
        mock_session.add.call_count == expected_entities_count
    ), f"Expected {expected_entities_count} entities created, but got {mock_session.add.call_count}"

    assert (
        mock_session.flush.call_count == expected_imported_count
    ), f"Expected {expected_imported_count} flush calls, but got {mock_session.flush.call_count}"


@pytest.mark.asyncio
async def test_import_radarr_movies_handles_partial_insert_failure(
    mock_session, mock_fetch_radarr_movies, mock_exists_result_false, sample_movies_basic
):
    """Test service handles partial insert failures with rollback"""
    # Arrange
    mock_fetch_radarr_movies.return_value = sample_movies_basic
    mock_session.execute.return_value = mock_exists_result_false

    # Simulate failure on second movie flush
    mock_session.flush.side_effect = [None, Exception("Flush failed")]

    expected_successful_imports = 1

    # Act
    imported_count = await import_radarr_movies(mock_session)

    # Assert
    assert (
        imported_count == expected_successful_imports
    ), f"Expected {expected_successful_imports} successful imports despite partial failure, but got {imported_count}"

    assert mock_session.rollback.call_count == 1, "Expected rollback after partial insert failure"

    assert (
        mock_session.commit.call_count == 1
    ), "Expected commit to be called even after partial failure"


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
    mock_session, radarr_movies_invalid_data, mock_fetch_radarr_movies, mock_exists_result_false
):
    """Test service skips movies without Radarr ID"""
    # Arrange
    mock_fetch_radarr_movies.return_value = radarr_movies_invalid_data
    mock_session.execute.return_value = mock_exists_result_false

    expected_valid_count = count_valid_movies(radarr_movies_invalid_data)
    expected_invalid_count = count_movies_without_id(radarr_movies_invalid_data)

    # Act
    imported_count = await import_radarr_movies(mock_session)

    # Assert
    assert (
        imported_count == expected_valid_count
    ), f"Expected to import {expected_valid_count} valid movies, but got {imported_count}"

    assert (
        mock_session.execute.call_count == expected_valid_count
    ), f"Expected existence checks only for {expected_valid_count} valid movies, but got {mock_session.execute.call_count}"

    # Optional: verify the total movies processed
    total_movies = len(radarr_movies_invalid_data)
    assert (
        expected_valid_count + expected_invalid_count == total_movies
    ), f"Movie count mismatch: {expected_valid_count} valid + {expected_invalid_count} invalid should equal {total_movies} total"
