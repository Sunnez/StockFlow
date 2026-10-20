from collections.abc import Sequence
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.errors import get_constraint_name
from app.models.inventory import Inventory
from app.models.order_item import OrderItem
from app.models.product import UQ_PRODUCTS_SKU, Product
from app.services.product.exceptions import (
    ProductNotFoundError,
    ProductSkuAlreadyExistsError,
    ProductUpdateError,
    ProductUsedInOrderError,
    ProductHasStockError,
)


async def create_product(
    db: AsyncSession,
    *,
    name: str,
    sku: str,
) -> Product:
    product = Product(
        name=name,
        sku=sku,
    )

    try:
        async with db.begin():
            db.add(product)
            await db.flush()

    except IntegrityError as exc:
        if (
            isinstance(exc.orig, UniqueViolation)
            and get_constraint_name(exc) == UQ_PRODUCTS_SKU
        ):
            raise ProductSkuAlreadyExistsError(sku) from exc

        raise

    return product


async def get_product(
    db: AsyncSession,
    *,
    product_id: UUID,
) -> Product:
    product = await db.get(Product, product_id)

    if product is None:
        raise ProductNotFoundError(product_id)

    return product


async def list_products(
    db: AsyncSession,
    *,
    limit: int,
    offset: int,
) -> Sequence[Product]:
    result = await db.execute(
        select(Product).order_by(Product.id).limit(limit).offset(offset)
    )

    return result.scalars().all()


async def update_product(
    db: AsyncSession,
    *,
    product_id: UUID,
    name: str | None,
    sku: str | None,
) -> Product:
    if name is None and sku is None:
        raise ProductUpdateError(product_id)
    try:
        async with db.begin():
            stmt = select(Product).where(Product.id == product_id).with_for_update()

            result = await db.execute(stmt)

            product = result.scalar_one_or_none()

            if product is None:
                raise ProductNotFoundError(product_id)
            if name is not None:
                product.name = name
            if sku is not None:
                product.sku = sku

            await db.flush()
    except IntegrityError as exc:
        if (
            isinstance(exc.orig, UniqueViolation)
            and get_constraint_name(exc) == UQ_PRODUCTS_SKU
            and sku is not None
        ):
            raise ProductSkuAlreadyExistsError(sku) from exc
        raise
    return product


async def delete_product(
    db: AsyncSession,
    *,
    product_id: UUID,
) -> None:
    async with db.begin():
        stmt = select(Product).where(Product.id == product_id).with_for_update()

        result = await db.execute(stmt)

        product = result.scalar_one_or_none()

        if product is None:
            raise ProductNotFoundError(product_id)

        stmt = (
            select(OrderItem.order_id)
            .where(OrderItem.product_id == product_id)
            .limit(1)
        )

        result = await db.execute(stmt)
        order_id = result.scalar_one_or_none()

        if order_id is not None:
            raise ProductUsedInOrderError(product_id, order_id)

        stmt = (
            select(Inventory)
            .where(Inventory.product_id == product_id)
            .with_for_update()
        )

        result = await db.execute(stmt)
        inventory_rows = result.scalars().all()
        if any(inventory.quantity > 0 for inventory in inventory_rows):
            raise ProductHasStockError(product_id)

        for inventory in inventory_rows:
            await db.delete(inventory)

        await db.delete(product)
        await db.flush()
