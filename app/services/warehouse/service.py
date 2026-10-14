from collections.abc import Sequence
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.errors import get_constraint_name
from app.models.warehouse import (
    UQ_WAREHOUSES_NAME,
    Warehouse,
)
from app.services.warehouse.exceptions import (
    WarehouseNameAlreadyExistsError,
    WarehouseNotFoundError,
)


async def create_warehouse(
    db: AsyncSession,
    *,
    name: str,
    location: str,
) -> Warehouse:
    warehouse = Warehouse(
        name=name,
        location=location,
    )

    try:
        async with db.begin():
            db.add(warehouse)
            await db.flush()

    except IntegrityError as exc:
        if (
            isinstance(exc.orig, UniqueViolation)
            and get_constraint_name(exc) == UQ_WAREHOUSES_NAME
        ):
            raise WarehouseNameAlreadyExistsError(name) from exc

        raise

    return warehouse


async def get_warehouse(
    db: AsyncSession,
    *,
    warehouse_id: UUID,
) -> Warehouse:
    warehouse = await db.get(Warehouse, warehouse_id)

    if warehouse is None:
        raise WarehouseNotFoundError(warehouse_id)

    return warehouse


async def list_warehouses(
    db: AsyncSession,
    *,
    limit: int,
    offset: int,
) -> Sequence[Warehouse]:
    result = await db.execute(
        select(Warehouse)
        .order_by(Warehouse.id)
        .limit(limit)
        .offset(offset)
    )

    return result.scalars().all()