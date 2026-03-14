from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AppUser, RefreshToken
from app.schemas.error_codes import AuthErrorCode
from app.utils.security import (
    create_access_token,
    generate_recovery_code,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)


async def is_setup_required(session: AsyncSession) -> bool:
    result = await session.execute(select(func.count()).select_from(AppUser))
    count = result.scalar_one()
    return count == 0


async def register_user(
    session: AsyncSession,
    username: str,
    password: str,
    email: str | None = None,
) -> tuple[AppUser, str]:
    if not await is_setup_required(session):
        raise HTTPException(
            status_code=403,
            detail={"code": AuthErrorCode.REGISTRATION_CLOSED},
        )

    existing = await session.execute(select(AppUser).where(AppUser.username == username))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail={"code": AuthErrorCode.USERNAME_TAKEN},
        )

    raw_recovery_code = generate_recovery_code()
    user = AppUser(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        recovery_code_hash=hash_token(raw_recovery_code),
        is_active=True,
    )
    session.add(user)
    await session.flush()

    return user, raw_recovery_code


async def authenticate_user(
    session: AsyncSession,
    username: str,
    password: str,
) -> AppUser:
    result = await session.execute(select(AppUser).where(AppUser.username == username))
    user = result.scalar_one_or_none()

    dummy_hash = "$2b$12$dummy"
    hashed = user.hashed_password if user is not None else dummy_hash
    password_valid = verify_password(password, hashed)

    if user is None or not password_valid:
        raise HTTPException(
            status_code=401,
            detail={"code": AuthErrorCode.INVALID_CREDENTIALS},
        )

    user.last_login_at = datetime.now(UTC)
    return user


async def create_refresh_token(
    session: AsyncSession,
    user_id: int,
    expires_days: int = 30,
) -> str:
    raw = generate_refresh_token()
    token = RefreshToken(
        user_id=user_id,
        token_hash=hash_token(raw),
        expires_at=datetime.now(UTC) + timedelta(days=expires_days),
        revoked=False,
    )
    session.add(token)
    await session.flush()
    return raw


async def refresh_access_token(
    session: AsyncSession,
    refresh_token_raw: str,
    secret: str,
    expires_minutes: int,
) -> tuple[str, str]:
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token_raw))
    )
    token = result.scalar_one_or_none()

    now = datetime.now(UTC)
    if token is None or token.revoked or token.expires_at <= now:
        raise HTTPException(
            status_code=401,
            detail={"code": AuthErrorCode.TOKEN_INVALID},
        )

    token.revoked = True

    new_access_token = create_access_token(token.user_id, secret, expires_minutes)
    new_refresh_token = await create_refresh_token(session, token.user_id, expires_days=30)

    return new_access_token, new_refresh_token


async def revoke_refresh_token(session: AsyncSession, refresh_token_raw: str) -> None:
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token_raw))
    )
    token = result.scalar_one_or_none()
    if token is not None:
        token.revoked = True


async def reset_password_with_code(
    session: AsyncSession,
    recovery_code: str,
    new_password: str,
) -> tuple[AppUser, str]:
    result = await session.execute(
        select(AppUser).where(AppUser.recovery_code_hash == hash_token(recovery_code))
    )
    matched_user = result.scalar_one_or_none()

    if matched_user is None:
        raise HTTPException(
            status_code=400,
            detail={"code": AuthErrorCode.INVALID_RECOVERY_CODE},
        )

    matched_user.hashed_password = hash_password(new_password)
    new_code = generate_recovery_code()
    matched_user.recovery_code_hash = hash_password(new_code)

    return matched_user, new_code


async def regenerate_recovery_code(session: AsyncSession, user: AppUser) -> str:
    new_code = generate_recovery_code()
    user.recovery_code_hash = hash_token(new_code)
    return new_code


async def change_password(
    session: AsyncSession,
    user: AppUser,
    current_password: str,
    new_password: str,
) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail={"code": AuthErrorCode.INVALID_CREDENTIALS},
        )

    user.hashed_password = hash_password(new_password)

    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked == False)  # noqa: E712
        .values(revoked=True)
    )


async def update_user_profile(
    session: AsyncSession,
    user: AppUser,
    username: str | None = None,
    email: str | None = None,
) -> AppUser:
    if username is not None:
        result = await session.execute(
            select(AppUser).where(AppUser.username == username, AppUser.id != user.id)
        )
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=409,
                detail={"code": AuthErrorCode.USERNAME_TAKEN},
            )
        user.username = username

    if email is not None:
        user.email = email

    return user
