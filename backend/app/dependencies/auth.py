import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import AppUser
from app.schemas.error_codes import AuthErrorCode
from app.utils.security import decode_access_token, get_jwt_secret

security_scheme = HTTPBearer()
optional_security_scheme = HTTPBearer(auto_error=False)


def _decode_token(token: str) -> dict[str, object]:
    secret = get_jwt_secret()
    try:
        return decode_access_token(token, secret)  # type: ignore[return-value]
    except jwt.ExpiredSignatureError as err:
        raise HTTPException(status_code=401, detail={"code": AuthErrorCode.TOKEN_EXPIRED}) from err
    except jwt.InvalidTokenError as err:
        raise HTTPException(status_code=401, detail={"code": AuthErrorCode.TOKEN_INVALID}) from err


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    session: AsyncSession = Depends(get_session),
) -> AppUser:
    payload = _decode_token(credentials.credentials)
    user_id = int(str(payload["sub"]))
    user = await session.get(AppUser, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail={"code": AuthErrorCode.USER_INACTIVE})
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security_scheme),
    session: AsyncSession = Depends(get_session),
) -> AppUser | None:
    if credentials is None:
        return None
    payload = _decode_token(credentials.credentials)
    user_id = int(str(payload["sub"]))
    user = await session.get(AppUser, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail={"code": AuthErrorCode.USER_INACTIVE})
    return user
