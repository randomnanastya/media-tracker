"""Unit tests for movie status mapping functions."""

import pytest

from app.models import MovieStatus
from app.services.movie_utils import map_radarr_status, map_tmdb_status

# --- map_radarr_status ---


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("announced", MovieStatus.ANNOUNCED),
        ("tba", MovieStatus.ANNOUNCED),
        ("inCinemas", MovieStatus.IN_CINEMAS),
        ("released", MovieStatus.RELEASED),
        ("deleted", MovieStatus.CANCELED),
    ],
)
def test_map_radarr_status_known(raw: str, expected: MovieStatus) -> None:
    assert map_radarr_status(raw) == expected


def test_map_radarr_status_none_input() -> None:
    assert map_radarr_status(None) is None


def test_map_radarr_status_empty_string() -> None:
    assert map_radarr_status("") is None


def test_map_radarr_status_unknown_returns_none(caplog: pytest.LogCaptureFixture) -> None:
    result = map_radarr_status("someNewRadarrStatus")
    assert result is None
    assert "someNewRadarrStatus" in caplog.text


# --- map_tmdb_status ---


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Rumored", MovieStatus.RUMORED),
        ("Planned", MovieStatus.ANNOUNCED),
        ("In Production", MovieStatus.IN_PRODUCTION),
        ("Post Production", MovieStatus.POST_PRODUCTION),
        ("Released", MovieStatus.RELEASED),
        ("Canceled", MovieStatus.CANCELED),
    ],
)
def test_map_tmdb_status_known(raw: str, expected: MovieStatus) -> None:
    assert map_tmdb_status(raw) == expected


def test_map_tmdb_status_none_input() -> None:
    assert map_tmdb_status(None) is None


def test_map_tmdb_status_empty_string() -> None:
    assert map_tmdb_status("") is None


def test_map_tmdb_status_unknown_returns_none(caplog: pytest.LogCaptureFixture) -> None:
    result = map_tmdb_status("Limbo")
    assert result is None
    assert "Limbo" in caplog.text
