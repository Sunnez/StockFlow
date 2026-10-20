import asyncio
import sys
from collections.abc import AsyncIterator

import app.models  # noqa: F401
import pytest
import pytest_asyncio
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def pytest_asyncio_loop_factories(
    config: pytest.Config,
    item: pytest.Item,
):
    if sys.platform == "win32":
        return {
            "selector": asyncio.SelectorEventLoop,
        }

    return {
        "default": asyncio.new_event_loop,
    }


if settings.test_database_url is None:
    raise RuntimeError("TEST_DATABASE_URL is not configured")


test_engine = create_async_engine(
    settings.test_database_url,
    pool_pre_ping=True,
)


TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db() -> AsyncIterator[AsyncSession]:
    async with TestSessionLocal() as session:
        yield session


async def clear_database() -> None:
    async with test_engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            await connection.execute(table.delete())


@pytest_asyncio.fixture(
    scope="session",
    loop_scope="session",
    autouse=True,
)
async def prepare_database() -> AsyncIterator[None]:
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_database() -> AsyncIterator[None]:
    await clear_database()

    yield

    await clear_database()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    fastapi_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(
        app=fastapi_app,
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as test_client:
        yield test_client

    fastapi_app.dependency_overrides.clear()
