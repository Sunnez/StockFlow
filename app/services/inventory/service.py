from collections.abc import Sequence
from uuid import UUID

from psycopg.errors import (
    CheckViolation,
    ForeignKeyViolation,
    UniqueViolation,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.errors import get_constraint_name
from app.models.inventory import (
    CK_INVENTORY_QUANTITY_NON_NEGATIVE,
    FK_INVENTORY_PRODUCT,
    FK_INVENTORY_WAREHOUSE,
    UQ_INVENTORY_PRODUCT_WAREHOUSE,
    Inventory,
)
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.services.inventory.exceptions import (
    InvalidInventoryQuantityError,
    InventoryAlreadyExistsError,
    InventoryNotFoundError,
    InventoryNotEmptyError,
)
from app.services.product.exceptions import ProductNotFoundError
from app.services.warehouse.exceptions import WarehouseNotFoundError


async def create_inventory(
    db: AsyncSession,
    *,
    warehouse_id: UUID,
    product_id: UUID,
    quantity: int,
) -> Inventory:
    if quantity < 0:
        raise InvalidInventoryQuantityError(quantity)

    try:
        async with db.begin():
            warehouse = await db.get(
                Warehouse,
                warehouse_id,
            )

            if warehouse is None:
                raise WarehouseNotFoundError(warehouse_id)

            product = await db.get(
                Product,
                product_id,
            )

            if product is None:
                raise ProductNotFoundError(product_id)

            inventory = Inventory(
                warehouse_id=warehouse_id,
                product_id=product_id,
                quantity=quantity,
            )

            db.add(inventory)

            await db.flush()

    except IntegrityError as exc:
        constraint_name = get_constraint_name(exc)

        if (
            isinstance(exc.orig, UniqueViolation)
            and constraint_name
            == UQ_INVENTORY_PRODUCT_WAREHOUSE
        ):
            raise InventoryAlreadyExistsError(
                product_id=product_id,
                warehouse_id=warehouse_id,
            ) from exc

        if isinstance(exc.orig, ForeignKeyViolation):
            if constraint_name == FK_INVENTORY_PRODUCT:
                raise ProductNotFoundError(
                    product_id
                ) from exc

            if constraint_name == FK_INVENTORY_WAREHOUSE:
                raise WarehouseNotFoundError(
                    warehouse_id
                ) from exc

        if (
            isinstance(exc.orig, CheckViolation)
            and constraint_name
            == CK_INVENTORY_QUANTITY_NON_NEGATIVE
        ):
            raise InvalidInventoryQuantityError(
                quantity
            ) from exc

        raise

    return inventory


async def list_warehouse_inventory(
    db: AsyncSession,
    *,
    warehouse_id: UUID,
    limit: int,
    offset: int,
) -> Sequence[Inventory]:
    warehouse = await db.get(
        Warehouse,
        warehouse_id,
    )

    if warehouse is None:
        raise WarehouseNotFoundError(warehouse_id)

    result = await db.execute(
        select(Inventory)
        .where(
            Inventory.warehouse_id == warehouse_id
        )
        .order_by(Inventory.id)
        .limit(limit)
        .offset(offset)
    )

    return result.scalars().all()


async def update_inventory_quantity(
    db: AsyncSession,
    *,
    warehouse_id: UUID,
    product_id: UUID,
    quantity: int,
) -> Inventory:
    if quantity < 0:
        raise InvalidInventoryQuantityError(quantity)

    try:
        async with db.begin():
            warehouse = await db.get(
                Warehouse,
                warehouse_id,
            )

            if warehouse is None:
                raise WarehouseNotFoundError(
                    warehouse_id
                )

            result = await db.execute(
                select(Inventory)
                .where(
                    Inventory.warehouse_id == warehouse_id,
                    Inventory.product_id == product_id,
                )
                .with_for_update()
            )

            inventory = result.scalar_one_or_none()

            if inventory is None:
                raise InventoryNotFoundError(
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                )

            inventory.quantity = quantity

            await db.flush()

    except IntegrityError as exc:
        constraint_name = get_constraint_name(exc)

        if (
            isinstance(exc.orig, CheckViolation)
            and constraint_name
            == CK_INVENTORY_QUANTITY_NON_NEGATIVE
        ):
            raise InvalidInventoryQuantityError(
                quantity
            ) from exc

        raise

    return inventory


async def delete_inventory(
    db: AsyncSession,
    *,
    warehouse_id: UUID,
    product_id: UUID,
) -> None:
    async with db.begin():
        stmt = (
            select(Inventory)
            .where(
                Inventory.warehouse_id == warehouse_id,
                Inventory.product_id == product_id,
            )
            .with_for_update()
        )

        result = await db.execute(stmt)
        inventory = result.scalar_one_or_none()

        if inventory is None:
            raise InventoryNotFoundError(
                product_id,
                warehouse_id,
            )

        if inventory.quantity > 0:
            raise InventoryNotEmptyError(
                product_id,
                warehouse_id,
            )

        await db.delete(inventory)
        await db.flush()