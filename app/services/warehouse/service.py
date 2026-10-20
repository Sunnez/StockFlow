from collections.abc import Sequence
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.errors import get_constraint_name
from app.models.inventory import Inventory
from app.models.warehouse import (
    UQ_WAREHOUSES_NAME,
    Warehouse,
)
from app.services.warehouse.exceptions import (
    WarehouseNameAlreadyExistsError,
    WarehouseNotFoundError,
    WarehouseUpdateError,
    WarehouseHasInventoryError,
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
        select(Warehouse).order_by(Warehouse.id).limit(limit).offset(offset)
    )

    return result.scalars().all()


async def update_warehouse(
    db: AsyncSession,
    *,
    warehouse_id: UUID,
    name: str | None,
    location: str | None,
) -> Warehouse:
    if name is None and location is None:
        raise WarehouseUpdateError(warehouse_id)
    try:
        async with db.begin():
            stmt = (
                select(Warehouse).where(Warehouse.id == warehouse_id).with_for_update()
            )
            result = await db.execute(stmt)
            warehouse = result.scalar_one_or_none()

            if warehouse is None:
                raise WarehouseNotFoundError(warehouse_id)
            if name is not None:
                warehouse.name = name
            if location is not None:
                warehouse.location = location

            await db.flush()
    except IntegrityError as exc:
        if (
            isinstance(exc.orig, UniqueViolation)
            and get_constraint_name(exc) == UQ_WAREHOUSES_NAME
            and name is not None
        ):
            raise WarehouseNameAlreadyExistsError(name) from exc
        raise

    return warehouse


async def delete_warehouse(
    db: AsyncSession,
    *,
    warehouse_id: UUID,
) -> None:
    async with db.begin():
        stmt = select(Warehouse).where(Warehouse.id == warehouse_id).with_for_update()

        result = await db.execute(stmt)

        warehouse = result.scalar_one_or_none()

        if warehouse is None:
            raise WarehouseNotFoundError(warehouse_id)

        stmt = (
            select(Inventory.id).where(Inventory.warehouse_id == warehouse_id).limit(1)
        )

        result = await db.execute(stmt)
        inventory_id = result.scalar_one_or_none()

        if inventory_id is not None:
            raise WarehouseHasInventoryError(warehouse_id)

        await db.delete(warehouse)
        await db.flush()
