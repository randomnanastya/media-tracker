import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import AppUser
from app.schemas.error_codes import AuthErrorCode
from app.utils.security import decode_access_token, get_jwt_secret


def _decode_token(token: str) -> dict[str, object]:
    secret = get_jwt_secret()
    try:
        return decode_access_token(token, secret)
    except jwt.ExpiredSignatureError as err:
        raise HTTPException(status_code=401, detail={"code": AuthErrorCode.TOKEN_EXPIRED}) from err
    except jwt.InvalidTokenError as err:
        raise HTTPException(status_code=401, detail={"code": AuthErrorCode.TOKEN_INVALID}) from err


def _extract_token(request: Request) -> str | None:
    token = request.cookies.get("access_token")
    if token is None:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    return token


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AppUser:
    token = _extract_token(request)
    if token is None:
        raise HTTPException(status_code=401, detail={"code": AuthErrorCode.TOKEN_INVALID})
    payload = _decode_token(token)
    user_id = int(str(payload["sub"]))
    user = await session.get(AppUser, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail={"code": AuthErrorCode.USER_INACTIVE})
    return user


async def get_optional_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AppUser | None:
    token = _extract_token(request)
    if token is None:
        return None
    payload = _decode_token(token)
    user_id = int(str(payload["sub"]))
    user = await session.get(AppUser, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail={"code": AuthErrorCode.USER_INACTIVE})
    return user
