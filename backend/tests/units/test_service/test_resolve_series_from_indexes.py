from app.services.series_utils import resolve_series_from_indexes
from tests.factories import SeriesFactory


def test_resolve_by_jellyfin_id() -> None:
    """Матч по jellyfin_id — возвращает нужный Series."""
    series = SeriesFactory.build(id=1, jellyfin_id="jf-111", tvdb_id="tvdb-111", imdb_id="tt111")

    result = resolve_series_from_indexes(
        jellyfin_id="jf-111",
        tvdb_id="tvdb-111",
        imdb_id="tt111",
        by_jellyfin_id={"jf-111": series},
        by_tvdb_id={},
        by_imdb_id={},
    )

    assert result is series


def test_resolve_by_tvdb_id_when_jellyfin_miss() -> None:
    """jellyfin_id не найден, матч по tvdb_id — возвращает нужный Series."""
    series = SeriesFactory.build(id=2, jellyfin_id="jf-old", tvdb_id="tvdb-222", imdb_id="tt222")

    result = resolve_series_from_indexes(
        jellyfin_id="jf-not-in-index",
        tvdb_id="tvdb-222",
        imdb_id="tt222",
        by_jellyfin_id={},
        by_tvdb_id={"tvdb-222": series},
        by_imdb_id={},
    )

    assert result is series


def test_resolve_by_imdb_id_when_others_miss() -> None:
    """jellyfin_id и tvdb_id не найдены, матч по imdb_id — возвращает нужный Series."""
    series = SeriesFactory.build(id=3, jellyfin_id="jf-old", tvdb_id="tvdb-old", imdb_id="tt333")

    result = resolve_series_from_indexes(
        jellyfin_id="jf-not-present",
        tvdb_id="tvdb-not-present",
        imdb_id="tt333",
        by_jellyfin_id={},
        by_tvdb_id={},
        by_imdb_id={"tt333": series},
    )

    assert result is series


def test_resolve_returns_none_when_all_miss() -> None:
    """Все три словаря пусты — возвращает None."""
    result = resolve_series_from_indexes(
        jellyfin_id="jf-x",
        tvdb_id="tvdb-x",
        imdb_id="tt-x",
        by_jellyfin_id={},
        by_tvdb_id={},
        by_imdb_id={},
    )

    assert result is None


def test_resolve_jellyfin_id_takes_priority_over_tvdb() -> None:
    """jellyfin_id имеет приоритет над tvdb_id — возвращается объект из by_jellyfin_id."""
    series_by_jf = SeriesFactory.build(id=10, jellyfin_id="jf-priority", tvdb_id="tvdb-shared")
    series_by_tvdb = SeriesFactory.build(id=20, jellyfin_id="jf-other", tvdb_id="tvdb-shared")

    result = resolve_series_from_indexes(
        jellyfin_id="jf-priority",
        tvdb_id="tvdb-shared",
        imdb_id=None,
        by_jellyfin_id={"jf-priority": series_by_jf},
        by_tvdb_id={"tvdb-shared": series_by_tvdb},
        by_imdb_id={},
    )

    assert result is series_by_jf
    assert result is not series_by_tvdb


def test_resolve_with_all_none_ids() -> None:
    """Все три ID равны None — пропускает все ступени и возвращает None."""
    series = SeriesFactory.build(id=5, jellyfin_id="jf-5", tvdb_id="tvdb-5", imdb_id="tt5")

    result = resolve_series_from_indexes(
        jellyfin_id=None,
        tvdb_id=None,
        imdb_id=None,
        by_jellyfin_id={"jf-5": series},
        by_tvdb_id={"tvdb-5": series},
        by_imdb_id={"tt5": series},
    )

    assert result is None
