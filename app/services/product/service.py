from collections.abc import Sequence
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.errors import get_constraint_name
from app.models.product import UQ_PRODUCTS_SKU, Product
from app.services.product.exceptions import (
    ProductNotFoundError,
    ProductSkuAlreadyExistsError,
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
        select(Product)
        .order_by(Product.id)
        .limit(limit)
        .offset(offset)
    )

    return result.scalars().all()