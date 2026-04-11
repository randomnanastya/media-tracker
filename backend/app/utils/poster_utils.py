from typing import Any


def extract_poster(images: list[dict[str, Any]]) -> str | None:
    """Extract poster remoteUrl from images list where coverType == 'poster'."""
    return next(
        (img.get("remoteUrl") for img in images if img.get("coverType") == "poster"),
        None,
    )
