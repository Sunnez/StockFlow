from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.csrf import generate_csrf_token
from app.auth.jwt import create_access_token
from app.core.config import settings
from app.db.session import get_db
from app.schemas.user import UserCreate, UserLogin, UserRead
from app.services.auth import service as auth_service
from app.services.auth.exceptions import InvalidRefreshTokenError
from app.services.auth.sessions import (
    create_auth_session,
    revoke_auth_session,
    rotate_refresh_token,
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await auth_service.register_user(
        db,
        email=data.email,
        password=data.password,
    )


@router.post(
    "/login",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
)
async def login_user(
    data: UserLogin,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user = await auth_service.authenticate_user(
        db,
        email=data.email,
        password=data.password,
    )

    auth_session, raw_refresh_token = await create_auth_session(
        db,
        user_id=user.id,
    )

    csrf_token = generate_csrf_token(auth_session.id)

    access_token = create_access_token(
        user_id=user.id,
        session_id=auth_session.id,
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.jwt_access_expire_minutes * 60,
        path="/",
    )

    response.set_cookie(
        key="refresh_token",
        value=raw_refresh_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.auth_session_expire_days * 24 * 60 * 60,
        path="/auth",
    )

    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.auth_session_expire_days * 24 * 60 * 60,
        path="/",
    )

    response.headers["Cache-Control"] = "no-store"

    return user


@router.post(
    "/refresh",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def refresh_access_token(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: Annotated[str | None, Cookie()] = None,
    csrf_cookie: Annotated[
        str | None,
        Cookie(alias="csrf_token"),
    ] = None,
    csrf_header: Annotated[
        str | None,
        Header(alias="X-CSRF-Token"),
    ] = None,
):
    if refresh_token is None:
        raise InvalidRefreshTokenError()

    rotated = await rotate_refresh_token(
        db,
        raw_token=refresh_token,
        csrf_cookie=csrf_cookie,
        csrf_header=csrf_header,
    )

    access_token = create_access_token(
        user_id=rotated.user_id,
        session_id=rotated.session_id,
    )

    remaining_seconds = max(
        1,
        int(
            (
                rotated.session_expires_at
                - datetime.now(UTC)
            ).total_seconds()
        ),
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.jwt_access_expire_minutes * 60,
        path="/",
    )

    response.set_cookie(
        key="refresh_token",
        value=rotated.refresh_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=remaining_seconds,
        path="/auth",
    )

    response.headers["Cache-Control"] = "no-store"


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout_user(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    access_token: Annotated[str | None, Cookie()] = None,
    refresh_token: Annotated[str | None, Cookie()] = None,
    csrf_cookie: Annotated[
        str | None,
        Cookie(alias="csrf_token"),
    ] = None,
    csrf_header: Annotated[
        str | None,
        Header(alias="X-CSRF-Token"),
    ] = None,
):
    await revoke_auth_session(
        db,
        raw_token=refresh_token,
        access_token=access_token,
        csrf_cookie=csrf_cookie,
        csrf_header=csrf_header,
    )

    response.delete_cookie(
        key="access_token",
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="lax",
    )

    response.delete_cookie(
        key="refresh_token",
        path="/auth",
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="lax",
    )

    response.delete_cookie(
        key="csrf_token",
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=False,
        samesite="lax",
    )

    response.headers["Cache-Control"] = "no-store"
