import asyncio
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
from tests.db_safety import UnsafeTestDatabase, validate_test_database_url
from tests.factories import create_user, login


def pytest_asyncio_loop_factories(config: pytest.Config, item: pytest.Item):
    if sys.platform == "win32":
        return {"selector": asyncio.SelectorEventLoop}
    return {"default": asyncio.new_event_loop}


@pytest.fixture(scope="session")
def test_engine():
    # No engine or connection exists before the pure guard succeeds.
    target = validate_test_database_url(
        settings.test_database_url,
        settings.database_url,
        reset_confirmation=os.environ.get("STOCKFLOW_ALLOW_TEST_DB_RESET"),
    )
    # NullPool prevents connections being reused across pytest event loops.
    return create_async_engine(target, poolclass=NullPool, echo=False)


@asynccontextmanager
async def guarded_transaction(engine):
    # Recheck the actual engine URL for setup AND every cleanup operation.
    target = validate_test_database_url(
        engine.url,
        settings.database_url,
        reset_confirmation=os.environ.get("STOCKFLOW_ALLOW_TEST_DB_RESET"),
    )
    async with engine.begin() as connection:
        identity = (
            await connection.execute(text("SELECT current_database(), current_user"))
        ).one()
        if tuple(identity) != (target.database, target.username):
            raise UnsafeTestDatabase(
                "Connected database identity does not match the approved test target"
            )
        yield connection


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def prepare_database(test_engine) -> AsyncIterator[None]:
    try:
        async with guarded_transaction(test_engine) as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
        yield
    finally:
        # Never bypass target verification even during teardown.
        try:
            async with guarded_transaction(test_engine) as connection:
                await connection.run_sync(Base.metadata.drop_all)
        finally:
            await test_engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_database(prepare_database, test_engine) -> AsyncIterator[None]:
    async def clear():
        async with guarded_transaction(test_engine) as connection:
            for table in reversed(Base.metadata.sorted_tables):
                await connection.execute(table.delete())

    await clear()
    try:
        yield
    finally:
        await clear()


@pytest.fixture
def db_sessions(test_engine):
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def client_factory(clean_database, db_sessions):
    async def override_get_db():
        async with db_sessions() as session:
            yield session

    previous = fastapi_app.dependency_overrides.copy()
    fastapi_app.dependency_overrides[get_db] = override_get_db

    @asynccontextmanager
    async def make_client():
        async with AsyncClient(
            transport=ASGITransport(app=fastapi_app),
            base_url="https://testserver",
            headers={"Origin": settings.auth_allowed_origins[0]},
        ) as test_client:
            yield test_client

    try:
        yield make_client
    finally:
        fastapi_app.dependency_overrides.clear()
        fastapi_app.dependency_overrides.update(previous)


@pytest_asyncio.fixture
async def client(client_factory):
    async with client_factory() as test_client:
        yield test_client


@pytest_asyncio.fixture
async def tenant_client(client):
    await create_user(client)
    await login(client)
    response = await client.post("/organizations", json={"name": "Test organization"})
    assert response.status_code == 201, response.text
    organization = response.json()
    client.base_url = f"https://testserver/organizations/{organization['id']}/"
    yield client
