from datetime import datetime, timezone
from typing import Annotated

import jwt
from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode_access_token
from app.core.exceptions import UnauthorizedError
from app.db.session import get_db
from app.models.auth_session import AuthSession
from app.models.user import User


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    access_token: Annotated[str | None, Cookie()] = None,
) -> User:
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
            or auth_session.expires_at <= datetime.now(timezone.utc)
        ):
            raise UnauthorizedError("Not authenticated")

        user = await db.get(User, user_id)

        if user is None or not user.is_active:
            raise UnauthorizedError("Not authenticated")

    return user