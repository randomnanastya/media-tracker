# tests/units/test_radarr_service.py
import pytest
from unittest.mock import AsyncMock, Mock, patch, call
from datetime import datetime, timezone

from app.services.radarr_service import import_radarr_movies
from app.models import Media, Movie, MediaType


@pytest.mark.asyncio
async def test_import_radarr_movies_creates_both_entities():
    """Test service creates both Media and Movie entities for each movie"""
    # Arrange
    mock_session = AsyncMock()
    sample_movies = [
        {
            "id": 1,
            "title": "Movie 1",
            "inCinemas": "2023-01-01T00:00:00Z"
        },
        {
            "id": 2,
            "title": "Movie 2",
            "inCinemas": "2023-02-01T00:00:00Z"
        }
    ]

    with patch("app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = sample_movies

        # Mock exists check - все фильмы новые
        mock_result = Mock()
        mock_result.scalar.return_value = False
        mock_session.execute.return_value = mock_result

        # Mock DB operations
        mock_session.add = Mock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        # Act
        result = await import_radarr_movies(mock_session)

        # Assert - проверяем бизнес-логику и взаимодействие с БД
        assert result == 2  # Импортировано 2 фильма

        # Проверяем вызовы проверки существования
        assert mock_session.execute.call_count == 2

        # Проверяем создание сущностей - семантика вместо количества
        assert mock_session.add.call_count == 4  # 2 Media + 2 Movie

        # Проверяем что flush вызывался для каждой пары сущностей
        assert mock_session.flush.call_count == 2

        # Проверяем коммит
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_import_radarr_movies_skips_existing_movies():
    """Test service skips movies that already exist in database"""
    # Arrange
    mock_session = AsyncMock()
    sample_movies = [
        {
            "id": 1,
            "title": "Existing Movie",
            "inCinemas": "2023-01-01T00:00:00Z"
        },
        {
            "id": 2,
            "title": "New Movie",
            "inCinemas": "2023-02-01T00:00:00Z"
        }
    ]

    with patch("app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = sample_movies

        # Mock exists check - первый существует, второй новый
        mock_result = Mock()
        mock_result.scalar.side_effect = [True, False]  # Первый существует
        mock_session.execute.return_value = mock_result

        # Mock DB operations
        mock_session.add = Mock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        # Act
        result = await import_radarr_movies(mock_session)

        # Assert
        assert result == 1  # Только один новый фильм импортирован

        # Проверяем что для существующего фильма не создавались сущности
        assert mock_session.add.call_count == 2  # Только для второго фильма (1 Media + 1 Movie)
        assert mock_session.flush.call_count == 1  # Только один flush


@pytest.mark.asyncio
async def test_import_radarr_movies_handles_partial_insert_failure():
    """Test service handles partial insert failures with rollback"""
    # Arrange
    mock_session = AsyncMock()
    sample_movies = [
        {
            "id": 1,
            "title": "Movie 1",
            "inCinemas": "2023-01-01T00:00:00Z"
        },
        {
            "id": 2,
            "title": "Movie 2",
            "inCinemas": "2023-02-01T00:00:00Z"
        }
    ]

    with patch("app.services.radarr_movies.fetch_radarr_movies", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = sample_movies

        # Mock exists check - все новые
        mock_result = Mock()
        mock_result.scalar.return_value = False
        mock_session.execute.return_value = mock_result

        # Mock flush to fail on second movie
        mock_session.add = Mock()
        mock_session.flush = AsyncMock()
        mock_session.flush.side_effect = [None, Exception("Flush failed")]
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        # Act
        result = await import_radarr_movies(mock_session)

        # Assert
        assert result == 1  # Только один успешный импорт

        # Проверяем откат при ошибке
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_called_once()  # Коммит все равно должен быть


@pytest.mark.asyncio
async def test_import_radarr_movies_handles_commit_failure():
    """Test service handles commit failure"""
    # Arrange
    mock_session = AsyncMock()
    sample_movies = [
        {
            "id": 1,
            "title": "Movie 1",
            "inCinemas": "2023-01-01T00:00:00Z"
        }
    ]

    with patch("app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = sample_movies

        # Mock exists check
        mock_result = Mock()
        mock_result.scalar.return_value = False
        mock_session.execute.return_value = mock_result

        # Mock commit to fail
        mock_session.add = Mock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.commit.side_effect = Exception("Commit failed")
        mock_session.rollback = AsyncMock()

        # Act & Assert
        with pytest.raises(Exception, match="Commit failed"):
            await import_radarr_movies(mock_session)

        # Проверяем что откат был вызван при ошибке коммита
        mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_import_radarr_movies_skips_movies_without_id():
    """Test service skips movies without Radarr ID"""
    # Arrange
    mock_session = AsyncMock()
    sample_movies = [
        {
            "title": "Movie without ID"  # Нет id поля
        },
        {
            "id": 2,
            "title": "Valid Movie",
            "inCinemas": "2023-02-01T00:00:00Z"
        }
    ]

    with patch("app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = sample_movies

        # Mock exists check только для валидного фильма
        mock_result = Mock()
        mock_result.scalar.return_value = False
        mock_session.execute.return_value = mock_result

        mock_session.add = Mock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        # Act
        result = await import_radarr_movies(mock_session)

        # Assert
        assert result == 1  # Только один валидный фильм

        # Проверяем что execute вызывался только для валидного фильма
        assert mock_session.execute.call_count == 1