"""Unit tests for series status mapping functions."""

import pytest

from app.models import SeriesStatus
from app.services.series_utils import (
    map_jellyfin_series_status,
    map_sonarr_series_status,
    map_tmdb_series_status,
)

# --- map_tmdb_series_status ---


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Returning Series", SeriesStatus.CONTINUING),
        ("In Production", SeriesStatus.IN_PRODUCTION),
        ("Planned", SeriesStatus.PLANNED),
        ("Pilot", SeriesStatus.PLANNED),
        ("Ended", SeriesStatus.ENDED),
        ("Canceled", SeriesStatus.CANCELED),
    ],
)
def test_map_tmdb_series_status_known(raw: str, expected: SeriesStatus) -> None:
    assert map_tmdb_series_status(raw) == expected


def test_map_tmdb_series_status_none_input() -> None:
    assert map_tmdb_series_status(None) is None


def test_map_tmdb_series_status_unknown_returns_none(caplog: pytest.LogCaptureFixture) -> None:
    result = map_tmdb_series_status("Unknown")
    assert result is None
    assert "Unknown" in caplog.text


def test_map_tmdb_series_status_unknown_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    import logging

    with caplog.at_level(logging.WARNING):
        map_tmdb_series_status("SomeFutureStatus")
    assert "SomeFutureStatus" in caplog.text


def test_map_tmdb_series_status_case_sensitive() -> None:
    # Маппинг регистрозависим: строчная версия не должна совпадать
    assert map_tmdb_series_status("returning series") is None
    assert map_tmdb_series_status("ended") is None
    assert map_tmdb_series_status("canceled") is None


# --- map_sonarr_series_status ---


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("continuing", SeriesStatus.CONTINUING),
        ("ended", SeriesStatus.ENDED),
        ("upcoming", SeriesStatus.IN_PRODUCTION),
        ("deleted", SeriesStatus.DELETED),
    ],
)
def test_map_sonarr_series_status_known(raw: str, expected: SeriesStatus) -> None:
    assert map_sonarr_series_status(raw) == expected


def test_map_sonarr_series_status_none_input() -> None:
    assert map_sonarr_series_status(None) is None


def test_map_sonarr_series_status_unknown_returns_none(caplog: pytest.LogCaptureFixture) -> None:
    result = map_sonarr_series_status("paused")
    assert result is None
    assert "paused" in caplog.text


def test_map_sonarr_series_status_unknown_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    import logging

    with caplog.at_level(logging.WARNING):
        map_sonarr_series_status("future_status")
    assert "future_status" in caplog.text


def test_map_sonarr_series_status_case_sensitive() -> None:
    # Sonarr статусы строчные — заглавные не должны совпадать
    assert map_sonarr_series_status("Continuing") is None
    assert map_sonarr_series_status("Ended") is None
    assert map_sonarr_series_status("Upcoming") is None


# --- map_jellyfin_series_status ---


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Continuing", SeriesStatus.CONTINUING),
        ("Ended", SeriesStatus.ENDED),
        ("Unreleased", SeriesStatus.IN_PRODUCTION),
    ],
)
def test_map_jellyfin_series_status_known(raw: str, expected: SeriesStatus) -> None:
    assert map_jellyfin_series_status(raw) == expected


def test_map_jellyfin_series_status_none_input() -> None:
    assert map_jellyfin_series_status(None) is None


def test_map_jellyfin_series_status_unknown_returns_none(caplog: pytest.LogCaptureFixture) -> None:
    result = map_jellyfin_series_status("Hiatus")
    assert result is None
    assert "Hiatus" in caplog.text


def test_map_jellyfin_series_status_unknown_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    import logging

    with caplog.at_level(logging.WARNING):
        map_jellyfin_series_status("SomeUnknownStatus")
    assert "SomeUnknownStatus" in caplog.text


def test_map_jellyfin_series_status_case_sensitive() -> None:
    # Jellyfin statuses are case-sensitive — lowercase should not match
    assert map_jellyfin_series_status("continuing") is None
    assert map_jellyfin_series_status("ended") is None
    assert map_jellyfin_series_status("unreleased") is None
