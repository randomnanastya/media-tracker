from app.services.movie_utils import resolve_movie_from_indexes
from tests.factories import MovieFactory


def test_resolve_by_jellyfin_id() -> None:
    """jellyfin_id совпадает — возвращается нужный Movie."""
    target = MovieFactory.build(jellyfin_id="jf-abc", tmdb_id="tmdb-1", imdb_id="tt-1")
    other = MovieFactory.build(jellyfin_id="jf-other", tmdb_id="tmdb-other", imdb_id="tt-other")

    result = resolve_movie_from_indexes(
        jellyfin_id="jf-abc",
        tmdb_id=None,
        imdb_id=None,
        by_jellyfin_id={"jf-abc": target, "jf-other": other},
        by_tmdb_id={},
        by_imdb_id={},
    )

    assert result is target


def test_resolve_by_tmdb_id_when_jellyfin_miss() -> None:
    """jellyfin_id отсутствует в словаре, tmdb_id совпадает — возвращается Movie по tmdb."""
    target = MovieFactory.build(jellyfin_id=None, tmdb_id="tmdb-999", imdb_id="tt-999")

    result = resolve_movie_from_indexes(
        jellyfin_id="jf-unknown",
        tmdb_id="tmdb-999",
        imdb_id=None,
        by_jellyfin_id={},
        by_tmdb_id={"tmdb-999": target},
        by_imdb_id={},
    )

    assert result is target


def test_resolve_by_imdb_id_when_others_miss() -> None:
    """jellyfin_id и tmdb_id не совпадают, только imdb_id совпадает — возвращается Movie по imdb."""
    target = MovieFactory.build(jellyfin_id=None, tmdb_id=None, imdb_id="tt-777")

    result = resolve_movie_from_indexes(
        jellyfin_id="jf-miss",
        tmdb_id="tmdb-miss",
        imdb_id="tt-777",
        by_jellyfin_id={},
        by_tmdb_id={},
        by_imdb_id={"tt-777": target},
    )

    assert result is target


def test_resolve_returns_none_when_all_miss() -> None:
    """Все три словаря пусты — возвращается None."""
    result = resolve_movie_from_indexes(
        jellyfin_id="jf-x",
        tmdb_id="tmdb-x",
        imdb_id="tt-x",
        by_jellyfin_id={},
        by_tmdb_id={},
        by_imdb_id={},
    )

    assert result is None


def test_resolve_jellyfin_id_takes_priority_over_tmdb() -> None:
    """Один Movie в by_jellyfin_id, другой в by_tmdb_id — возвращается из by_jellyfin_id."""
    jellyfin_movie = MovieFactory.build(jellyfin_id="jf-1", tmdb_id="tmdb-1")
    tmdb_movie = MovieFactory.build(jellyfin_id=None, tmdb_id="tmdb-1")

    result = resolve_movie_from_indexes(
        jellyfin_id="jf-1",
        tmdb_id="tmdb-1",
        imdb_id=None,
        by_jellyfin_id={"jf-1": jellyfin_movie},
        by_tmdb_id={"tmdb-1": tmdb_movie},
        by_imdb_id={},
    )

    assert result is jellyfin_movie
    assert result is not tmdb_movie


def test_resolve_with_none_jellyfin_id() -> None:
    """jellyfin_id=None — первая ступень пропускается, Movie находится по tmdb_id."""
    target = MovieFactory.build(jellyfin_id=None, tmdb_id="tmdb-42")

    result = resolve_movie_from_indexes(
        jellyfin_id=None,
        tmdb_id="tmdb-42",
        imdb_id=None,
        by_jellyfin_id={"tmdb-42": MovieFactory.build()},  # ключ не совпадёт — jellyfin_id None
        by_tmdb_id={"tmdb-42": target},
        by_imdb_id={},
    )

    assert result is target


def test_resolve_with_all_none_ids() -> None:
    """Все три ID равны None — ни одна ступень не срабатывает, возвращается None."""
    result = resolve_movie_from_indexes(
        jellyfin_id=None,
        tmdb_id=None,
        imdb_id=None,
        by_jellyfin_id={"some-id": MovieFactory.build()},
        by_tmdb_id={"tmdb-1": MovieFactory.build()},
        by_imdb_id={"tt-1": MovieFactory.build()},
    )

    assert result is None
