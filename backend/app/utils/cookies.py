import os

from fastapi import Response


def set_access_token_cookie(response: Response, token: str, max_age_seconds: int) -> None:
    is_prod = os.getenv("APP_ENV") == "production"
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        path="/api",
        max_age=max_age_seconds,
    )


def set_refresh_token_cookie(response: Response, token: str, max_age_seconds: int) -> None:
    is_prod = os.getenv("APP_ENV") == "production"
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        path="/api/v1/auth",
        max_age=max_age_seconds,
    )


def clear_auth_cookies(response: Response) -> None:
    is_prod = os.getenv("APP_ENV") == "production"
    response.delete_cookie(
        key="access_token", path="/api", httponly=True, secure=is_prod, samesite="lax"
    )
    response.delete_cookie(
        key="refresh_token", path="/api/v1/auth", httponly=True, secure=is_prod, samesite="lax"
    )
