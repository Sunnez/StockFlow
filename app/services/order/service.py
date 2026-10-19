from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.schemas.order_item import OrderItemCreate
from app.domain.order import OrderStatus
from app.services.order.exceptions import (
    DuplicateProductInOrderError,
    EmptyOrderError,
    OrderCannotBeUpdatedError,
    OrderNotFoundError,
    ProductsNotFoundInOrderError,
    OrderCannotBeDeletedError,
)


async def create_order(
        db: AsyncSession,
        *,
        items: list[OrderItemCreate],
) -> Order:
    if not items:
        raise EmptyOrderError()
    seen_product_ids: set[UUID] = set()

    for item in items:
        if item.product_id in seen_product_ids:
            raise DuplicateProductInOrderError(item.product_id)

        seen_product_ids.add(item.product_id)

    async with db.begin():
        stmt = (
            select(Product.id)
            .where(Product.id.in_(seen_product_ids))
            .with_for_update(read=True, key_share=True)
        )
        result = await db.execute(stmt)
        existing_product_ids: set[UUID] = set(result.scalars().all())

        missing_product_ids = seen_product_ids - existing_product_ids

        if missing_product_ids:
            raise ProductsNotFoundInOrderError(missing_product_ids)

        order_items = [
            OrderItem(
                product_id=item.product_id,
                quantity=item.quantity,
                position=position,
            )
            for position, item in enumerate(items, start=1)
        ]

        order = Order(
            items=order_items,
        )

        db.add(order)
        await db.flush()


    return order


async def list_orders(
        db: AsyncSession,
        *,
        limit: int,
        offset: int,
) -> Sequence[Order]:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(limit)
        .offset(offset)
    )

    return result.scalars().all()


async def get_order(
        db: AsyncSession,
        *,
        order_id: UUID,
) -> Order:
    stmt = (
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items))
    )
    result = await db.execute(stmt)

    order = result.scalar_one_or_none()

    if order is None:
        raise OrderNotFoundError(order_id)

    return order


async def update_order(
        db: AsyncSession,
        *,
        order_id: UUID,
        new_items: list[OrderItemCreate],
) -> Order:
    if not new_items:
        raise EmptyOrderError()
    seen_product_ids: set[UUID] = set()

    for item in new_items:
        if item.product_id in seen_product_ids:
            raise DuplicateProductInOrderError(item.product_id)

        seen_product_ids.add(item.product_id)
    async with db.begin():
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items))
            .with_for_update()
        )

        result = await db.execute(stmt)

        existing_order = result.scalar_one_or_none()

        if existing_order is None:
            raise OrderNotFoundError(order_id)

        if existing_order.status != OrderStatus.PENDING:
            raise OrderCannotBeUpdatedError(order_id, existing_order.status)

        stmt = (
            select(Product.id)
            .where(Product.id.in_(seen_product_ids))
            .with_for_update(read=True, key_share=True)
        )

        result = await db.execute(stmt)

        existing_product_ids: set[UUID] = set(result.scalars().all())

        missing_product_ids = seen_product_ids - existing_product_ids
        if missing_product_ids:
            raise ProductsNotFoundInOrderError(missing_product_ids)

        order_items = [
            OrderItem(
                product_id=item.product_id,
                quantity=item.quantity,
                position=position,
            )
            for position, item in enumerate(new_items, start=1)
        ]

        existing_order.items.clear()
        await db.flush()

        existing_order.items.extend(order_items)
        await db.flush()

    return existing_order


async def delete_order(
        db: AsyncSession,
        *,
        order_id: UUID,
) -> None:
    async with db.begin():
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .with_for_update()
        )

        result = await db.execute(stmt)

        order = result.scalar_one_or_none()

        if order is None:
            raise OrderNotFoundError(order_id)

        if order.status != OrderStatus.PENDING:
            raise OrderCannotBeDeletedError(order_id, order.status)

        await db.delete(order)

        await db.flush()
