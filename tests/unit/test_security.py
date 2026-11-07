from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.middleware.security import trusted_request_source
from app.auth.csrf import generate_csrf_token, verify_csrf_token
from app.db.session import get_db
from app.main import app


def test_csrf_is_bound_to_session_and_requires_matching_header():
    session_id = uuid4()
    token = generate_csrf_token(session_id)
    assert verify_csrf_token(session_id, token, token)
    assert not verify_csrf_token(uuid4(), token, token)
    assert not verify_csrf_token(session_id, token, token + "x")
    assert not verify_csrf_token(session_id, token, None)
    assert not verify_csrf_token(session_id, None, token)


@pytest.mark.parametrize("token", ["", "bad", "x" * 257, "?.abc", "a." + "0" * 64])
def test_csrf_rejects_malformed_input(token):
    assert not verify_csrf_token(uuid4(), token, token)


@pytest.mark.parametrize(
    "origin,referer,expected",
    [
        ("https://testserver", None, True),
        (None, "https://testserver/docs", True),
        (None, None, False),
        ("null", "https://testserver/docs", False),
        ("https://evil.invalid", "https://testserver/docs", False),
        ("https://testserver.evil.invalid", None, False),
        ("http://testserver", None, False),
        (None, "https://user:secret@testserver/docs", False),
        (None, "https://testserver.evil.invalid/docs", False),
    ],
)
def test_exact_source_allowlist(origin, referer, expected):
    assert trusted_request_source(origin, referer) is expected


@pytest.mark.asyncio
async def test_http_security_and_openapi_without_database():
    async def deny_db():
        yield object()  # dependency resolves, but no SQL/session operations exist

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = deny_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="https://testserver"
        ) as client:
            assert (await client.get("/health")).status_code == 200
            for origin in (None, "null", "https://evil.invalid"):
                headers = {} if origin is None else {"Origin": origin}
                response = await client.post("/auth/login", json={}, headers=headers)
                assert response.status_code == 403
            response = await client.post(
                "/auth/login", json={}, headers={"Origin": "https://testserver"}
            )
            assert response.status_code == 422
            preflight = await client.options(
                "/organizations",
                headers={
                    "Origin": "https://testserver",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "X-CSRF-Token,Content-Type",
                },
            )
            assert preflight.status_code == 200
            assert preflight.headers["access-control-allow-credentials"] == "true"
            assert (
                preflight.headers["access-control-allow-origin"] == "https://testserver"
            )
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_openapi_cookie_auth_and_no_legacy_routes():
    schema = app.openapi()
    scheme = schema["components"]["securitySchemes"]["AccessCookie"]
    assert scheme["in"] == "cookie" and scheme["name"] == "access_token"
    assert schema["paths"]["/users/me"]["get"]["security"] == [{"AccessCookie": []}]
    assert "security" not in schema["paths"]["/auth/login"]["post"]
    assert "security" not in schema["paths"]["/auth/logout"]["post"]
    assert (
        len([operation for path in schema["paths"].values() for operation in path])
        == 35
    )
    assert all(
        path not in schema["paths"] for path in ("/products", "/warehouses", "/orders")
    )
