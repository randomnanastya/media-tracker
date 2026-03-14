import os

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import get_current_user
from app.models import AppUser
from app.schemas.auth import (
    AuthStatusResponse,
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RecoveryCodeResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    TokenResponse,
    UpdateUserRequest,
    UserResponse,
)
from app.services import auth_service
from app.utils.security import create_access_token, get_jwt_secret

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.get("/status", response_model=AuthStatusResponse)
async def get_status(
    session: AsyncSession = Depends(get_session),
) -> AuthStatusResponse:
    setup_required = await auth_service.is_setup_required(session)
    return AuthStatusResponse(setup_required=setup_required)


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> RegisterResponse:
    user, recovery_code = await auth_service.register_user(
        session, body.username, body.password, body.email
    )
    response = RegisterResponse(username=user.username, recovery_code=recovery_code)
    await session.commit()
    return response


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    expires_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    expires_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

    user = await auth_service.authenticate_user(session, body.username, body.password)
    secret = get_jwt_secret()
    access_token = create_access_token(user.id, secret, expires_minutes)
    refresh_token = await auth_service.create_refresh_token(session, user.id, expires_days)
    await session.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    secret = get_jwt_secret()
    expires_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))

    access_token, refresh_token = await auth_service.refresh_access_token(
        session, body.refresh_token, secret, expires_minutes
    )
    await session.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_minutes * 60,
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    body: ResetPasswordRequest,
    session: AsyncSession = Depends(get_session),
) -> ResetPasswordResponse:
    _, new_code = await auth_service.reset_password_with_code(
        session, body.recovery_code, body.new_password
    )
    await session.commit()
    return ResetPasswordResponse(message="Password reset successful", new_recovery_code=new_code)


@router.post("/logout", response_model=dict[str, str])
async def logout(
    body: LogoutRequest,
    session: AsyncSession = Depends(get_session),
    current_user: AppUser = Depends(get_current_user),
) -> dict[str, str]:
    await auth_service.revoke_refresh_token(session, body.refresh_token)
    await session.commit()
    return {"message": "ok"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: AppUser = Depends(get_current_user),
) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at,
    )


@router.put("/me", response_model=UserResponse)
async def update_me(
    body: UpdateUserRequest,
    session: AsyncSession = Depends(get_session),
    current_user: AppUser = Depends(get_current_user),
) -> UserResponse:
    user = await auth_service.update_user_profile(session, current_user, body.username, body.email)
    response = UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )
    await session.commit()
    return response


@router.put("/me/password", response_model=dict[str, str])
async def change_password(
    body: ChangePasswordRequest,
    session: AsyncSession = Depends(get_session),
    current_user: AppUser = Depends(get_current_user),
) -> dict[str, str]:
    await auth_service.change_password(
        session, current_user, body.current_password, body.new_password
    )
    await session.commit()
    return {"message": "ok"}


@router.get("/recovery-code", response_model=RecoveryCodeResponse)
async def get_recovery_code(
    session: AsyncSession = Depends(get_session),
    current_user: AppUser = Depends(get_current_user),
) -> RecoveryCodeResponse:
    code = await auth_service.regenerate_recovery_code(session, current_user)
    await session.commit()
    return RecoveryCodeResponse(recovery_code=code)
