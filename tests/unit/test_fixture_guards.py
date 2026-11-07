"""Only mock the lazy fixture helpers; never execute a PostgreSQL test fixture."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.engine import make_url

from app.core.config import settings
from tests.db_safety import UnsafeTestDatabase
from tests.integration.conftest import (
    guarded_transaction,
)
from tests.integration.conftest import (
    test_engine as engine_fixture,
)

MAIN = "postgresql+psycopg://stockflow:synthetic@127.0.0.1:5433/stockflow"
TARGET = "postgresql+psycopg://stockflow_test:synthetic@127.0.0.1:5434/stockflow_test"


def test_fixture_refuses_to_create_engine_without_explicit_reset_marker(monkeypatch):
    factory = MagicMock()
    monkeypatch.delenv("STOCKFLOW_ALLOW_TEST_DB_RESET", raising=False)
    monkeypatch.setattr("tests.integration.conftest.create_async_engine", factory)
    with pytest.raises(UnsafeTestDatabase):
        engine_fixture.__wrapped__()
    factory.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_target_rechecked_before_connection(monkeypatch):
    monkeypatch.setenv("STOCKFLOW_ALLOW_TEST_DB_RESET", "stockflow_test")
    monkeypatch.setattr(settings, "database_url", MAIN)
    engine = MagicMock(url=make_url(MAIN))
    async_with_assert = False
    with pytest.raises(UnsafeTestDatabase):
        async with guarded_transaction(engine):
            async_with_assert = True
    assert not async_with_assert
    engine.begin.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "identity", [("stockflow", "stockflow_test"), ("stockflow_test", "stockflow")]
)
async def test_connected_identity_mismatch_never_yields_for_writes(
    monkeypatch, identity
):
    monkeypatch.setenv("STOCKFLOW_ALLOW_TEST_DB_RESET", "stockflow_test")
    monkeypatch.setattr(settings, "database_url", MAIN)
    engine = MagicMock(url=make_url(TARGET))
    connection = AsyncMock()
    result = MagicMock()
    result.one.return_value = identity
    connection.execute.return_value = result
    engine.begin.return_value.__aenter__ = AsyncMock(return_value=connection)
    engine.begin.return_value.__aexit__ = AsyncMock(return_value=False)
    with pytest.raises(UnsafeTestDatabase):
        async with guarded_transaction(engine) as guarded:
            await guarded.run_sync(MagicMock())
    connection.run_sync.assert_not_awaited()
    connection.execute.assert_awaited_once()  # identity SELECT only
