from unittest.mock import MagicMock, patch

from fastapi import Response

from app.utils.cookies import clear_auth_cookies, set_access_token_cookie, set_refresh_token_cookie


def test_set_access_token_cookie_dev() -> None:
    response = MagicMock(spec=Response)
    with patch.dict("os.environ", {"APP_ENV": "testing"}):
        set_access_token_cookie(response, "token123", 900)
    response.set_cookie.assert_called_once_with(
        key="access_token",
        value="token123",
        httponly=True,
        secure=False,
        samesite="lax",
        path="/api",
        max_age=900,
    )


def test_set_access_token_cookie_prod() -> None:
    response = MagicMock(spec=Response)
    with patch.dict("os.environ", {"APP_ENV": "production"}):
        set_access_token_cookie(response, "token123", 900)
    response.set_cookie.assert_called_once_with(
        key="access_token",
        value="token123",
        httponly=True,
        secure=True,
        samesite="lax",
        path="/api",
        max_age=900,
    )


def test_set_refresh_token_cookie_dev() -> None:
    response = MagicMock(spec=Response)
    with patch.dict("os.environ", {"APP_ENV": "testing"}):
        set_refresh_token_cookie(response, "refresh123", 2592000)
    response.set_cookie.assert_called_once_with(
        key="refresh_token",
        value="refresh123",
        httponly=True,
        secure=False,
        samesite="lax",
        path="/api/v1/auth",
        max_age=2592000,
    )


def test_set_refresh_token_cookie_prod() -> None:
    response = MagicMock(spec=Response)
    with patch.dict("os.environ", {"APP_ENV": "production"}):
        set_refresh_token_cookie(response, "refresh123", 2592000)
    response.set_cookie.assert_called_once_with(
        key="refresh_token",
        value="refresh123",
        httponly=True,
        secure=True,
        samesite="lax",
        path="/api/v1/auth",
        max_age=2592000,
    )


def test_clear_auth_cookies_dev() -> None:
    response = MagicMock(spec=Response)
    with patch.dict("os.environ", {"APP_ENV": "testing"}):
        clear_auth_cookies(response)
    assert response.delete_cookie.call_count == 2
    response.delete_cookie.assert_any_call(
        key="access_token",
        path="/api",
        httponly=True,
        secure=False,
        samesite="lax",
    )
    response.delete_cookie.assert_any_call(
        key="refresh_token",
        path="/api/v1/auth",
        httponly=True,
        secure=False,
        samesite="lax",
    )


def test_clear_auth_cookies_prod() -> None:
    response = MagicMock(spec=Response)
    with patch.dict("os.environ", {"APP_ENV": "production"}):
        clear_auth_cookies(response)
    assert response.delete_cookie.call_count == 2
    response.delete_cookie.assert_any_call(
        key="access_token",
        path="/api",
        httponly=True,
        secure=True,
        samesite="lax",
    )
    response.delete_cookie.assert_any_call(
        key="refresh_token",
        path="/api/v1/auth",
        httponly=True,
        secure=True,
        samesite="lax",
    )
