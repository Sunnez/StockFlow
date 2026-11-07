from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Cookie, Depends, Header
from fastapi.security import APIKeyCookie
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.csrf import verify_csrf_token
from app.auth.jwt import decode_access_token
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.db.session import get_db
from app.models.auth_session import AuthSession
from app.models.user import User

access_cookie = APIKeyCookie(
    name="access_token",
    scheme_name="AccessCookie",
    auto_error=False,
    description=(
        "HttpOnly cookie issued by POST /auth/login. Browser requests must include "
        "credentials. Unsafe requests also require a trusted Origin/Referer and "
        "the signed csrf_token cookie copied to X-CSRF-Token."
    ),
)


@dataclass(frozen=True)
class AuthContext:
    user: User
    session_id: UUID


async def get_auth_context(
    db: Annotated[AsyncSession, Depends(get_db)],
    access_token: Annotated[str | None, Depends(access_cookie)] = None,
) -> AuthContext:
    if access_token is None:
        raise UnauthorizedError("Not authenticated")

    try:
        user_id, session_id = decode_access_token(access_token)
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Not authenticated") from exc

    async with db.begin():
        auth_session = await db.get(AuthSession, session_id)

        if (
            auth_session is None
            or auth_session.user_id != user_id
            or auth_session.revoked_at is not None
            or auth_session.expires_at <= datetime.now(UTC)
        ):
            raise UnauthorizedError("Not authenticated")

        user = await db.get(User, user_id)

        if user is None or not user.is_active:
            raise UnauthorizedError("Not authenticated")

    return AuthContext(
        user=user,
        session_id=session_id,
    )


async def get_current_user(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> User:
    return auth.user


async def require_csrf(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    csrf_cookie: Annotated[
        str | None,
        Cookie(alias="csrf_token"),
    ] = None,
    csrf_header: Annotated[
        str | None,
        Header(alias="X-CSRF-Token"),
    ] = None,
) -> None:
    if not verify_csrf_token(
        auth.session_id,
        csrf_cookie,
        csrf_header,
    ):
        raise ForbiddenError("Invalid CSRF token")
