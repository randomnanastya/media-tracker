from app.models import Media, MediaType, Series
from app.services.series_utils import update_existing_series


def _make_series(poster_url: str | None = None) -> Series:
    media = Media(media_type=MediaType.SERIES, title="Test Series")
    series = Series(id=1, poster_url=poster_url)
    series.media = media
    return series


def test_update_existing_series_sets_poster_url_when_none() -> None:
    """poster_url проставляется если был None."""
    series = _make_series(poster_url=None)
    updated = update_existing_series(series, "Test Series", poster_url="http://new.jpg")
    assert updated is True
    assert series.poster_url == "http://new.jpg"


def test_update_existing_series_updates_poster_url_when_changed() -> None:
    """poster_url обновляется когда он изменился (не только если None)."""
    series = _make_series(poster_url="http://old.jpg")
    updated = update_existing_series(series, "Test Series", poster_url="http://new.jpg")
    assert updated is True
    assert series.poster_url == "http://new.jpg"


def test_update_existing_series_skips_poster_url_when_same() -> None:
    """poster_url не обновляется если не изменился."""
    series = _make_series(poster_url="http://same.jpg")
    updated = update_existing_series(series, "Test Series", poster_url="http://same.jpg")
    assert updated is False
    assert series.poster_url == "http://same.jpg"
