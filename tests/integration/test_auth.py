from uuid import UUID

import pytest
from httpx import AsyncClient

from app.auth.jwt import decode_access_token
from tests.factories import create_user

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
    assert str(decode_access_token(access_token)) == user["id"]

    cookie_header = response.headers["set-cookie"].lower()

    assert "httponly" in cookie_header
    assert "samesite=lax" in cookie_header
    assert "max-age=900" in cookie_header
    assert response.headers["cache-control"] == "no-store"


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
    assert response.json()["detail"] == (
        "Invalid email or password"
    )

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
    assert response.json()["detail"] == (
        "Invalid email or password"
    )

    assert "set-cookie" not in response.headers