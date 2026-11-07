"""Pure, fail-closed integration target validation. Never opens a connection."""

import re

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError


class UnsafeTestDatabase(RuntimeError):
    """The requested destructive test target has not been explicitly isolated."""


def validate_test_database_url(
    test_url: str | URL | None,
    main_url: str | URL,
    *,
    reset_confirmation: str | None,
) -> URL:
    # Exact marker deliberately cannot be enabled by a generic truthy value.
    if reset_confirmation != "stockflow_test":
        raise UnsafeTestDatabase(
            "Set STOCKFLOW_ALLOW_TEST_DB_RESET=stockflow_test only for an approved disposable database"
        )
    if not test_url:
        raise UnsafeTestDatabase("TEST_DATABASE_URL is required")
    try:
        target = make_url(test_url)
        main = make_url(main_url)
        target_port = target.port
    except (ValueError, TypeError, ArgumentError):
        # Do not include the URL or parser error (may contain a password).
        raise UnsafeTestDatabase("Invalid database URL") from None
    if (
        target.drivername != "postgresql+psycopg"
        or main.get_backend_name() != "postgresql"
    ):
        raise UnsafeTestDatabase("PostgreSQL psycopg test URL required")
    if target.host not in {"localhost", "127.0.0.1", "::1"} or target_port is None:
        raise UnsafeTestDatabase(
            "Test database must use an explicit local TCP host and port"
        )
    # libpq query options can override host/dbname/user or change search_path.
    if target.query or main.query:
        raise UnsafeTestDatabase(
            "Database URL query options are forbidden during integration tests"
        )
    if not main.database or not main.username or not main.host:
        raise UnsafeTestDatabase(
            "An explicit main database identity is required for comparison"
        )
    if target.database != "stockflow_test" or target.database == main.database:
        raise UnsafeTestDatabase("A distinct database named stockflow_test is required")
    if (
        not target.username
        or not re.fullmatch(r"[a-z][a-z0-9_]*_test", target.username)
        or target.username == main.username
    ):
        raise UnsafeTestDatabase(
            "A distinct dedicated role ending in _test is required"
        )
    return target
