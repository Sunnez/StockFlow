import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.csrf import verify_csrf_token
from app.auth.refresh_tokens import (
    generate_refresh_token,
    hash_refresh_secret,
    parse_refresh_token,
)
from app.core.config import settings
from app.core.exceptions import ForbiddenError
from app.models.auth_session import AuthSession
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.auth.exceptions import InvalidRefreshTokenError


async def create_auth_session(
    db: AsyncSession,
    *,
    user_id: UUID,
) -> tuple[AuthSession, str]:

    token_id, raw_token, token_hash = generate_refresh_token()

    auth_session = AuthSession(
        user_id=user_id,
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(days=settings.auth_session_expire_days)
        ),
    )

    async with db.begin():
        db.add(auth_session)
        await db.flush()

        refresh_token = RefreshToken(
            id=token_id,
            session_id=auth_session.id,
            token_hash=token_hash,
        )

        db.add(refresh_token)
        await db.flush()

    return auth_session, raw_token


@dataclass(frozen=True)
class RotatedCredentials:
    user_id: UUID
    session_id: UUID
    refresh_token: str
    session_expires_at: datetime


async def rotate_refresh_token(
    db: AsyncSession,
    *,
    raw_token: str,
    csrf_cookie: str | None,
    csrf_header: str | None,
) -> RotatedCredentials:

    try:
        token_id, secret = parse_refresh_token(raw_token)
    except (ValueError, TypeError) as exc:
        raise InvalidRefreshTokenError() from exc

    provided_hash = hash_refresh_secret(secret)

    reused = False
    result: RotatedCredentials | None = None

    async with db.begin():

        # Find the session associated with the presented token.
        session_id = await db.scalar(
            select(RefreshToken.session_id)
            .where(RefreshToken.id == token_id)
        )

        if session_id is None:
            raise InvalidRefreshTokenError()

        # Serialize all refresh operations for this session.
        auth_session = await db.scalar(
            select(AuthSession)
            .where(AuthSession.id == session_id)
            .with_for_update()
        )

        if auth_session is None:
            raise InvalidRefreshTokenError()

        # Read the token after acquiring the session lock.
        stored_token = await db.get(RefreshToken, token_id)

        if stored_token is None:
            raise InvalidRefreshTokenError()

        if not hmac.compare_digest(
            provided_hash,
            stored_token.token_hash,
        ):
            raise InvalidRefreshTokenError()

        if not verify_csrf_token(
            auth_session.id,
            csrf_cookie,
            csrf_header,
        ):
            raise ForbiddenError("Invalid CSRF token")
        

        now = datetime.now(timezone.utc)

        if (
            auth_session.revoked_at is not None
            or auth_session.expires_at <= now
        ):
            raise InvalidRefreshTokenError()

        if stored_token.used_at is not None:
            # Valid secret, but the token has already been used.
            auth_session.revoked_at = now
            reused = True

        else:
            user = await db.get(User, auth_session.user_id)

            if user is None or not user.is_active:
                raise InvalidRefreshTokenError()

            # Consume the old token.
            stored_token.used_at = now

            # Generate the next refresh token.
            new_token_id, new_raw_token, new_token_hash = (
                generate_refresh_token()
            )

            new_token = RefreshToken(
                id=new_token_id,
                session_id=auth_session.id,
                token_hash=new_token_hash,
            )

            db.add(new_token)

            result = RotatedCredentials(
                user_id=user.id,
                session_id=auth_session.id,
                refresh_token=new_raw_token,
                session_expires_at=auth_session.expires_at,
            )

    # The transaction has already committed here.
    if reused:
        raise InvalidRefreshTokenError()

    if result is None:
        raise InvalidRefreshTokenError()

    return result


async def revoke_auth_session(
    db: AsyncSession,
    *,
    raw_token: str,
    csrf_cookie: str | None,
    csrf_header: str | None,
) -> None:

    try:
        token_id, secret = parse_refresh_token(raw_token)
    except (ValueError, TypeError):
        return

    provided_hash = hash_refresh_secret(secret)

    async with db.begin():
        session_id = await db.scalar(
            select(RefreshToken.session_id)
            .where(RefreshToken.id == token_id)
        )

        if session_id is None:
            return

        auth_session = await db.scalar(
            select(AuthSession)
            .where(AuthSession.id == session_id)
            .with_for_update()
        )

        if auth_session is None:
            return

        stored_token = await db.get(
            RefreshToken,
            token_id,
        )

        if (
            stored_token is None
            or not hmac.compare_digest(
                provided_hash,
                stored_token.token_hash,
            )
        ):
            return

        if not verify_csrf_token(
            auth_session.id,
            csrf_cookie,
            csrf_header,
        ):
            raise ForbiddenError("Invalid CSRF token")

        if auth_session.revoked_at is None:
            auth_session.revoked_at = datetime.now(timezone.utc)