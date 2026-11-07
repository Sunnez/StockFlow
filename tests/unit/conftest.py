"""Unit tests use synthetic settings and fail if a real DB connection is tried.

Run this suite separately from PostgreSQL integration tests. Dotenv is disabled
while importing settings, so a local .env is not needed or read.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import SecretStr
from pydantic_settings import DotEnvSettingsSource

_UNIT_ENV = {
    "DATABASE_URL": "postgresql+psycopg://unit:synthetic@127.0.0.1:1/unit",
    "TEST_DATABASE_URL": "",
    "JWT_SECRET_KEY": "unit-only-jwt-key-with-at-least-32-bytes",
    "CSRF_SECRET_KEY": "unit-only-csrf-key-with-at-least-32-bytes",
    "AUTH_ALLOWED_ORIGINS": '["https://testserver"]',
    "AUTH_COOKIE_SECURE": "true",
    "JWT_ACCESS_EXPIRE_MINUTES": "15",
    "AUTH_SESSION_EXPIRE_DAYS": "30",
    "DB_ECHO": "false",
}
with (
    patch.dict(os.environ, _UNIT_ENV),
    # __call__ is too late: the source reads files during construction.
    patch.object(DotEnvSettingsSource, "_read_env_files", return_value={}),
):
    from app.core.config import settings


@pytest.fixture(autouse=True)
def isolated_unit_environment(monkeypatch):
    import psycopg
    from sqlalchemy.engine import Engine
    from sqlalchemy.ext.asyncio import AsyncEngine

    def deny_connection(*args, **kwargs):
        raise AssertionError("Unit tests must never connect to a database")

    for cls in (Engine, AsyncEngine, psycopg.Connection, psycopg.AsyncConnection):
        monkeypatch.setattr(cls, "connect", deny_connection)
    monkeypatch.setattr(psycopg, "connect", deny_connection)
    monkeypatch.setattr(settings, "auth_allowed_origins", ["https://testserver"])
    monkeypatch.setattr(
        settings, "jwt_secret_key", SecretStr(_UNIT_ENV["JWT_SECRET_KEY"])
    )
    monkeypatch.setattr(
        settings, "csrf_secret_key", SecretStr(_UNIT_ENV["CSRF_SECRET_KEY"])
    )
    monkeypatch.setattr(settings, "auth_cookie_secure", True)
