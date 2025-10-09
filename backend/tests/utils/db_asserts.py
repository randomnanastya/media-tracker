from typing import Any
from sqlalchemy.orm import DeclarativeMeta

def to_dict(model: DeclarativeMeta, exclude: set[str] = None) -> dict[str, Any]:
    """Преобразует SQLAlchemy модель в словарь."""
    exclude = exclude or set()
    return {
        c.name: getattr(model, c.name)
        for c in model.__table__.columns
        if c.name not in exclude
    }

def assert_model_matches(model, expected: dict[str, Any], exclude=None):
    """Сравнивает ORM-модель с ожидаемыми значениями и показывает различия."""
    exclude = set(exclude or [])
    model_dict = to_dict(model, exclude)

    # Словари для сравнения
    actual_filtered = {k: v for k, v in model_dict.items() if k in expected}

    if expected != actual_filtered:
        diffs = []
        for k in expected:
            if expected[k] != actual_filtered.get(k):
                diffs.append(
                    f"{k}: expected={expected[k]!r}, actual={actual_filtered.get(k)!r}"
                )
        raise AssertionError(
            f"{model.__class__.__name__} mismatch:\n" + "\n".join(diffs)
        )