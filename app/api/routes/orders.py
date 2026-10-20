from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.order import OrderCreate, OrderRead, OrderUpdate
from app.services.order import service as order_service

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_order(
    data: OrderCreate,
    db: AsyncSession = Depends(get_db),
):
    return await order_service.create_order(
        db,
        items=data.items,
    )


@router.get(
    "",
    response_model=list[OrderRead],
)
async def list_orders(
    db: AsyncSession = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return await order_service.list_orders(
        db,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{order_id}",
    response_model=OrderRead,
)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await order_service.get_order(
        db,
        order_id=order_id,
    )


@router.patch(
    "/{order_id}",
    response_model=OrderRead,
)
async def update_order(
    order_id: UUID,
    data: OrderUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await order_service.update_order(
        db,
        order_id=order_id,
        new_items=data.items,
    )


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    await order_service.delete_order(db, order_id=order_id)


@router.post(
    "/{order_id}/allocate",
    response_model=OrderRead,
)
async def allocate_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await order_service.allocate_order(
        db,
        order_id=order_id,
    )


@router.post(
    "/{order_id}/fulfill",
    response_model=OrderRead,
)
async def fulfill_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await order_service.fulfill_order(
        db,
        order_id=order_id,
    )


@router.post(
    "/{order_id}/cancel",
    response_model=OrderRead,
)
async def cancel_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await order_service.cancel_order(
        db,
        order_id=order_id,
    )
