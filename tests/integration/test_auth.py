from datetime import UTC
from http.cookies import SimpleCookie
from uuid import UUID

import pytest
from httpx import AsyncClient

from app.auth.jwt import decode_access_token
from app.core.config import settings
from tests.factories import create_user, login

pytestmark = pytest.mark.asyncio


async def test_register_user(client: AsyncClient):
    response = await client.post(
        "/auth/register",
        json={
            "email": "Alex@Example.com",
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert UUID(body["id"])
    assert body["email"] == "alex@example.com"
    assert body["is_active"] is True
    assert body["created_at"] is not None

    assert "password" not in body
    assert "password_hash" not in body


async def test_register_duplicate_email(client: AsyncClient):
    first_response = await client.post(
        "/auth/register",
        json={
            "email": "alex@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert first_response.status_code == 201

    duplicate_response = await client.post(
        "/auth/register",
        json={
            "email": "ALEX@EXAMPLE.COM",
            "password": "AnotherSecurePassword123!",
        },
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == (
        "User with this email already exists"
    )


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            {
                "email": "invalid-email",
                "password": "SecurePassword123!",
            },
            id="invalid-email",
        ),
        pytest.param(
            {
                "email": "alex@example.com",
                "password": "short",
            },
            id="short-password",
        ),
        pytest.param(
            {
                "email": "alex@example.com",
            },
            id="missing-password",
        ),
        pytest.param(
            {
                "email": "alex@example.com",
                "password": "SecurePassword123!",
                "is_superuser": True,
            },
            id="extra-field",
        ),
    ],
)
async def test_register_invalid_payload(
    client: AsyncClient,
    payload: dict,
):
    response = await client.post(
        "/auth/register",
        json=payload,
    )

    assert response.status_code == 422


async def test_login_success(client: AsyncClient):
    user = await create_user(client)

    response = await client.post(
        "/auth/login",
        json={
            "email": "ALEX@EXAMPLE.COM",
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == user["id"]
    assert body["email"] == user["email"]

    assert "password" not in body
    assert "password_hash" not in body

    access_token = response.cookies.get("access_token")

    assert access_token is not None
    user_id, session_id = decode_access_token(access_token)
    assert str(user_id) == user["id"]
    assert isinstance(session_id, UUID)

    cookie_header = response.headers.get_list("set-cookie")[0].lower()

    assert "httponly" in cookie_header
    assert "samesite=lax" in cookie_header
    assert f"max-age={settings.jwt_access_expire_minutes * 60}" in cookie_header
    assert response.headers["cache-control"] == "no-store"
    cookies = SimpleCookie()
    for header in response.headers.get_list("set-cookie"):
        cookies.load(header)
    for name, path, httponly in (
        ("access_token", "/", True),
        ("refresh_token", "/auth", True),
        ("csrf_token", "/", False),
    ):
        assert cookies[name]["path"] == path
        assert bool(cookies[name]["httponly"]) is httponly
        assert bool(cookies[name]["secure"]) is settings.auth_cookie_secure
        assert cookies[name]["samesite"].lower() == "lax"
    assert not {"access_token", "refresh_token", "csrf_token"} & body.keys()


async def test_login_wrong_password(client: AsyncClient):
    await create_user(client)

    response = await client.post(
        "/auth/login",
        json={
            "email": "alex@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == ("Invalid email or password")

    assert "set-cookie" not in response.headers


async def test_login_unknown_email(client: AsyncClient):
    response = await client.post(
        "/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == ("Invalid email or password")

    assert "set-cookie" not in response.headers


async def test_cookie_auth_lifecycle_and_access_revocation(client):
    await create_user(client)
    await login(client)
    assert (await client.get("/users/me")).status_code == 200
    previous_refresh = client.cookies["refresh_token"]
    response = await client.post("/auth/refresh")
    assert response.status_code == 204
    assert client.cookies["refresh_token"] != previous_refresh
    assert response.headers["cache-control"] == "no-store"
    access = client.cookies["access_token"]
    assert (await client.post("/auth/logout")).status_code == 204
    assert not any(
        name in client.cookies
        for name in ("access_token", "refresh_token", "csrf_token")
    )
    client.cookies.set("access_token", access, path="/")
    assert (await client.get("/users/me")).status_code == 401
    client.cookies.clear()
    assert (await client.post("/auth/logout")).status_code == 204


@pytest.mark.parametrize(
    "refresh_state", ["missing", "malformed", "unknown", "wrong-secret"]
)
async def test_logout_access_fallback_revokes_server_session(client, refresh_state):
    await create_user(client)
    await login(client)
    access = client.cookies["access_token"]
    previous_refresh = client.cookies["refresh_token"]
    client.cookies.delete("refresh_token")
    if refresh_state != "missing":
        value = {
            "malformed": "malformed",
            "unknown": "00000000-0000-0000-0000-000000000000.unknown",
            "wrong-secret": previous_refresh.split(".")[0] + ".wrong-secret",
        }[refresh_state]
        client.cookies.set("refresh_token", value, path="/auth")
    assert (await client.post("/auth/logout")).status_code == 204
    client.cookies.set("access_token", access, path="/")
    assert (await client.get("/users/me")).status_code == 401


@pytest.mark.parametrize(
    "endpoint", ["/auth/refresh", "/auth/logout", "/organizations"]
)
@pytest.mark.parametrize("csrf_kind", ["missing", "mismatch", "other-session"])
async def test_session_mutation_rejects_invalid_csrf(client, endpoint, csrf_kind):
    from uuid import uuid4

    from app.auth.csrf import generate_csrf_token

    await create_user(client)
    await login(client)
    if csrf_kind == "missing":
        client.headers.pop("X-CSRF-Token")
    elif csrf_kind == "mismatch":
        client.headers["X-CSRF-Token"] = "mismatch"
    else:
        other = generate_csrf_token(uuid4())
        client.cookies.delete("csrf_token")
        client.cookies.set("csrf_token", other, path="/")
        client.headers["X-CSRF-Token"] = other
    response = await client.post(
        endpoint, json={"name": "Denied"} if endpoint == "/organizations" else None
    )
    assert response.status_code == 403
    assert "set-cookie" not in response.headers
    assert (await client.get("/users/me")).status_code == 200


async def test_refresh_replay_revokes_whole_session(client):
    await create_user(client)
    await login(client)
    old = client.cookies["refresh_token"]
    assert (await client.post("/auth/refresh")).status_code == 204
    client.cookies.delete("refresh_token")
    client.cookies.set("refresh_token", old, path="/auth")
    assert (await client.post("/auth/refresh")).status_code == 401
    assert (await client.get("/users/me")).status_code == 401


async def test_logout_only_revokes_current_session(client, client_factory):
    await create_user(client)
    await login(client)
    async with client_factory() as second:
        await login(second)
        assert (await client.post("/auth/logout")).status_code == 204
        assert (await second.get("/users/me")).status_code == 200
        assert (await second.post("/auth/refresh")).status_code == 204


async def test_refresh_can_recover_missing_access_and_logout_uses_refresh(client):
    await create_user(client)
    await login(client)
    client.cookies.delete("access_token")
    assert (await client.get("/users/me")).status_code == 401
    assert (await client.post("/auth/refresh")).status_code == 204
    assert (await client.get("/users/me")).status_code == 200
    client.cookies.delete("access_token")
    assert (await client.post("/auth/logout")).status_code == 204


@pytest.mark.parametrize("origin", [None, "null", "https://evil.invalid"])
async def test_login_requires_trusted_origin(client, origin):
    client.headers.pop("Origin")
    headers = {} if origin is None else {"Origin": origin}
    response = await client.post(
        "/auth/login",
        headers=headers,
        json={"email": "alex@example.com", "password": "SecurePassword123!"},
    )
    assert response.status_code == 403


@pytest.mark.parametrize("state", ["expired", "inactive"])
async def test_server_session_or_user_state_invalidates_auth(
    client, db_sessions, state
):
    from datetime import datetime, timedelta

    from app.models.auth_session import AuthSession
    from app.models.user import User

    await create_user(client)
    await login(client)
    user_id, session_id = decode_access_token(client.cookies["access_token"])
    async with db_sessions() as db, db.begin():
        if state == "expired":
            session = await db.get(AuthSession, session_id)
            session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        else:
            user = await db.get(User, user_id)
            user.is_active = False
    assert (await client.get("/users/me")).status_code == 401
    assert (await client.post("/auth/refresh")).status_code == 401


async def test_logout_prefers_access_session_over_unrelated_refresh_cookie(
    client, client_factory
):
    await create_user(client)
    await login(client)
    async with client_factory() as second:
        await login(second)
        first_access = client.cookies["access_token"]
        client.cookies.delete("refresh_token")
        client.cookies.set(
            "refresh_token", second.cookies["refresh_token"], path="/auth"
        )
        assert (await client.post("/auth/logout")).status_code == 204
        client.cookies.set("access_token", first_access, path="/")
        assert (await client.get("/users/me")).status_code == 401
        assert (await second.get("/users/me")).status_code == 200
        assert (await second.post("/auth/refresh")).status_code == 204
