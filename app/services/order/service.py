from collections import defaultdict
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.order import OrderStatus
from app.models.inventory import Inventory
from app.models.order import Order
from app.models.order_allocation import OrderAllocation
from app.models.order_item import OrderItem
from app.models.product import Product
from app.schemas.order_item import OrderItemCreate
from app.services.order.exceptions import (
    DuplicateProductInOrderError,
    EmptyOrderError,
    InsufficientInventoryError,
    InventoryReservationMismatchError,
    OrderCannotBeAllocatedError,
    OrderCannotBeCancelledError,
    OrderCannotBeDeletedError,
    OrderCannotBeFulfilledError,
    OrderCannotBeUpdatedError,
    OrderNotFoundError,
    ProductsNotFoundInOrderError,
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
                allocations=[],
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
        .options(selectinload(Order.items).selectinload(OrderItem.allocations))
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
        .options(selectinload(Order.items).selectinload(OrderItem.allocations))
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
            .options(selectinload(Order.items).selectinload(OrderItem.allocations))
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
                allocations=[],
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
        stmt = select(Order).where(Order.id == order_id).with_for_update()

        result = await db.execute(stmt)

        order = result.scalar_one_or_none()

        if order is None:
            raise OrderNotFoundError(order_id)

        if order.status != OrderStatus.PENDING:
            raise OrderCannotBeDeletedError(order_id, order.status)

        await db.delete(order)

        await db.flush()


async def allocate_order(
    db: AsyncSession,
    *,
    order_id: UUID,
) -> Order:
    async with db.begin():
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items).selectinload(OrderItem.allocations))
            .with_for_update()
        )

        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if order is None:
            raise OrderNotFoundError(order_id)

        if order.status != OrderStatus.PENDING:
            raise OrderCannotBeAllocatedError(order_id, order.status)

        product_ids = {item.product_id for item in order.items}

        stmt = (
            select(Inventory)
            .where(Inventory.product_id.in_(product_ids))
            .order_by(
                Inventory.product_id,
                Inventory.warehouse_id,
                Inventory.id,
            )
            .with_for_update()
        )

        result = await db.execute(stmt)
        inventories = result.scalars().all()

        inventories_by_product: defaultdict[
            UUID,
            list[Inventory],
        ] = defaultdict(list)

        for inventory in inventories:
            inventories_by_product[inventory.product_id].append(inventory)

        for item in order.items:
            product_inventories = inventories_by_product[item.product_id]

            total_available = sum(
                inventory.available_quantity for inventory in product_inventories
            )

            if total_available < item.quantity:
                raise InsufficientInventoryError(
                    product_id=item.product_id,
                    requested_quantity=item.quantity,
                    available_quantity=total_available,
                )

            remaining_quantity = item.quantity

            for inventory in product_inventories:
                if remaining_quantity == 0:
                    break

                available_quantity = inventory.available_quantity

                if available_quantity <= 0:
                    continue

                allocated_quantity = min(remaining_quantity, available_quantity)

                inventory.reserved_quantity += allocated_quantity

                allocation = OrderAllocation(
                    inventory_id=inventory.id, quantity=allocated_quantity
                )

                item.allocations.append(allocation)

                remaining_quantity -= allocated_quantity

        order.status = OrderStatus.ALLOCATED

        await db.flush()

    return order


async def fulfill_order(
    db: AsyncSession,
    *,
    order_id: UUID,
) -> Order:
    async with db.begin():
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items).selectinload(OrderItem.allocations))
            .with_for_update()
        )

        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if order is None:
            raise OrderNotFoundError(order_id)

        if order.status != OrderStatus.ALLOCATED:
            raise OrderCannotBeFulfilledError(order_id, order.status)

        inventory_ids = {
            allocation.inventory_id
            for item in order.items
            for allocation in item.allocations
        }

        stmt = (
            select(Inventory)
            .where(Inventory.id.in_(inventory_ids))
            .order_by(
                Inventory.product_id,
                Inventory.warehouse_id,
                Inventory.id,
            )
            .with_for_update()
        )

        result = await db.execute(stmt)
        inventories = result.scalars().all()

        inventories_by_id = {inventory.id: inventory for inventory in inventories}

        for item in order.items:
            for allocation in item.allocations:
                inventory = inventories_by_id[allocation.inventory_id]

                if (
                    inventory.quantity < allocation.quantity
                    or inventory.reserved_quantity < allocation.quantity
                ):
                    raise InventoryReservationMismatchError(
                        inventory_id=inventory.id,
                        allocation_quantity=allocation.quantity,
                        quantity=inventory.quantity,
                        reserved_quantity=inventory.reserved_quantity,
                    )

                inventory.quantity -= allocation.quantity
                inventory.reserved_quantity -= allocation.quantity

        order.status = OrderStatus.FULFILLED

        await db.flush()

    return order


async def cancel_order(
    db: AsyncSession,
    *,
    order_id: UUID,
) -> Order:
    async with db.begin():
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items).selectinload(OrderItem.allocations))
            .with_for_update()
        )

        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if order is None:
            raise OrderNotFoundError(order_id)

        if order.status not in (
            OrderStatus.PENDING,
            OrderStatus.ALLOCATED,
        ):
            raise OrderCannotBeCancelledError(
                order_id,
                order.status,
            )

        if order.status == OrderStatus.ALLOCATED:
            inventory_ids = {
                allocation.inventory_id
                for item in order.items
                for allocation in item.allocations
            }

            stmt = (
                select(Inventory)
                .where(Inventory.id.in_(inventory_ids))
                .order_by(
                    Inventory.product_id,
                    Inventory.warehouse_id,
                    Inventory.id,
                )
                .with_for_update()
            )

            result = await db.execute(stmt)
            inventories = result.scalars().all()

            inventories_by_id = {inventory.id: inventory for inventory in inventories}

            for item in order.items:
                for allocation in item.allocations:
                    inventory = inventories_by_id[allocation.inventory_id]

                    if inventory.reserved_quantity < allocation.quantity:
                        raise InventoryReservationMismatchError(
                            inventory_id=inventory.id,
                            allocation_quantity=allocation.quantity,
                            quantity=inventory.quantity,
                            reserved_quantity=inventory.reserved_quantity,
                        )

                    inventory.reserved_quantity -= allocation.quantity

        order.status = OrderStatus.CANCELLED

        await db.flush()

    return order
