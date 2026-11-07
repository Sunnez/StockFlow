from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.api.dependencies.auth import get_auth_context
from app.auth.csrf import generate_csrf_token
from app.auth.jwt import create_access_token
from app.auth.refresh_tokens import generate_refresh_token
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.models.auth_session import AuthSession
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.auth.exceptions import InvalidRefreshTokenError
from app.services.auth.sessions import revoke_auth_session, rotate_refresh_token


def session_data():
    user = User(id=uuid4(), is_active=True)
    session = AuthSession(
        id=uuid4(),
        user_id=user.id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    db = AsyncMock()
    transaction = MagicMock()
    transaction.__aenter__ = AsyncMock()
    transaction.__aexit__ = AsyncMock(return_value=False)
    db.begin = MagicMock(return_value=transaction)
    db.add = MagicMock()
    return db, session, user, transaction


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "refresh", [None, "malformed", "unknown.secret", "wrong-secret"]
)
async def test_logout_revokes_active_access_session_even_with_unusable_refresh(refresh):
    db, session, user, _ = session_data()
    db.scalar.return_value = session
    db.get.return_value = user
    csrf = generate_csrf_token(session.id)
    await revoke_auth_session(
        db,
        raw_token=refresh,
        access_token=create_access_token(user.id, session.id),
        csrf_cookie=csrf,
        csrf_header=csrf,
    )
    assert session.revoked_at is not None
    db.scalar.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("csrf_kind", ["missing", "mismatch", "other-session"])
async def test_access_logout_never_bypasses_csrf(csrf_kind):
    db, session, user, transaction = session_data()
    db.scalar.return_value = session
    db.get.return_value = user
    csrf = generate_csrf_token(session.id if csrf_kind != "other-session" else uuid4())
    with pytest.raises(ForbiddenError):
        await revoke_auth_session(
            db,
            raw_token=None,
            access_token=create_access_token(user.id, session.id),
            csrf_cookie=csrf,
            csrf_header=None
            if csrf_kind == "missing"
            else (csrf + "x" if csrf_kind == "mismatch" else csrf),
        )
    assert session.revoked_at is None
    assert transaction.__aexit__.call_args.args[0] is ForbiddenError


@pytest.mark.asyncio
@pytest.mark.parametrize("access", [None, "invalid.jwt"])
async def test_public_logout_without_usable_credentials_is_idempotent(access):
    db, _, _, _ = session_data()
    await revoke_auth_session(
        db, raw_token=None, access_token=access, csrf_cookie=None, csrf_header=None
    )
    db.begin.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state",
    [
        "revoked",
        "expired",
        "wrong-user",
        "inactive-user",
        "missing-session",
        "missing-user",
    ],
)
async def test_access_context_rejects_invalid_server_state(state):
    db, session, user, _ = session_data()
    token = create_access_token(user.id, session.id)
    if state == "revoked":
        session.revoked_at = datetime.now(UTC)
    elif state == "expired":
        session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    elif state == "wrong-user":
        session.user_id = uuid4()
    elif state == "inactive-user":
        user.is_active = False
    db.get.side_effect = [
        None if state == "missing-session" else session,
        None if state == "missing-user" else user,
    ]
    with pytest.raises(UnauthorizedError):
        await get_auth_context(db=db, access_token=token)


@pytest.mark.asyncio
async def test_refresh_rotation_consumes_token_and_replay_commits_revocation():
    db, session, user, transaction = session_data()
    token_id, raw, token_hash = generate_refresh_token()
    stored = RefreshToken(id=token_id, session_id=session.id, token_hash=token_hash)
    db.scalar.side_effect = [session.id, session]
    db.get.side_effect = [stored, user]
    csrf = generate_csrf_token(session.id)
    rotated = await rotate_refresh_token(
        db, raw_token=raw, csrf_cookie=csrf, csrf_header=csrf
    )
    assert rotated.session_id == session.id and rotated.refresh_token != raw
    assert stored.used_at is not None
    assert session.revoked_at is None
    db.add.assert_called_once()
    db.scalar.side_effect = [session.id, session]
    db.get.side_effect = [stored]
    with pytest.raises(InvalidRefreshTokenError):
        await rotate_refresh_token(
            db, raw_token=raw, csrf_cookie=csrf, csrf_header=csrf
        )
    assert session.revoked_at is not None
    # Reuse error is raised AFTER a successful commit, not inside transaction.
    assert transaction.__aexit__.call_args.args == (None, None, None)


@pytest.mark.asyncio
async def test_bad_refresh_csrf_does_not_consume_or_revoke():
    db, session, _, _ = session_data()
    token_id, raw, token_hash = generate_refresh_token()
    stored = RefreshToken(id=token_id, session_id=session.id, token_hash=token_hash)
    db.scalar.side_effect = [session.id, session]
    db.get.return_value = stored
    with pytest.raises(ForbiddenError):
        await rotate_refresh_token(
            db, raw_token=raw, csrf_cookie=None, csrf_header=None
        )
    assert session.revoked_at is None and stored.used_at is None


@pytest.mark.asyncio
async def test_refresh_logout_still_works_without_access():
    db, session, _, _ = session_data()
    token_id, raw, token_hash = generate_refresh_token()
    db.scalar.side_effect = [session.id, session]
    db.get.return_value = RefreshToken(
        id=token_id, session_id=session.id, token_hash=token_hash
    )
    csrf = generate_csrf_token(session.id)
    await revoke_auth_session(
        db,
        raw_token=raw,
        access_token="invalid.jwt",
        csrf_cookie=csrf,
        csrf_header=csrf,
    )
    assert session.revoked_at is not None


@pytest.mark.asyncio
async def test_logout_http_route_passes_access_cookie_and_clears_matching_paths():
    from httpx import ASGITransport, AsyncClient

    from app.db.session import get_db
    from app.main import app

    db, session, user, _ = session_data()
    db.scalar.return_value = session
    db.get.side_effect = [user, session]
    csrf = generate_csrf_token(session.id)
    access = create_access_token(user.id, session.id)

    async def mock_get_db():
        yield db

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = mock_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="https://testserver",
            headers={"Origin": "https://testserver", "X-CSRF-Token": csrf},
        ) as client:
            client.cookies.set("access_token", access, path="/")
            client.cookies.set("csrf_token", csrf, path="/")
            response = await client.post("/auth/logout")
            assert response.status_code == 204
            assert session.revoked_at is not None
            assert response.headers["cache-control"] == "no-store"
            cookies = response.headers.get_list("set-cookie")
            assert len(cookies) == 3
            assert all("Max-Age=0" in cookie for cookie in cookies)
            assert any(
                "refresh_token=" in cookie and "Path=/auth" in cookie
                for cookie in cookies
            )
            assert any(
                "access_token=" in cookie and "Path=/;" in cookie for cookie in cookies
            )
            # Server session check rejects the pre-logout JWT even if replayed.
            client.cookies.set("access_token", access, path="/")
            assert (await client.get("/users/me")).status_code == 401
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["missing", "expired", "wrong-user", "inactive"])
async def test_logout_access_fallback_does_not_revoke_an_invalid_context(state):
    db, session, user, _ = session_data()
    token = create_access_token(user.id, session.id)
    csrf = generate_csrf_token(session.id)
    if state == "expired":
        session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    elif state == "wrong-user":
        session.user_id = uuid4()
    elif state == "inactive":
        user.is_active = False
    db.scalar.return_value = None if state == "missing" else session
    db.get.return_value = user
    await revoke_auth_session(
        db, raw_token=None, access_token=token, csrf_cookie=csrf, csrf_header=csrf
    )
    assert session.revoked_at is None
