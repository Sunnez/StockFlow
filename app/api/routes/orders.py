from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.order import OrderCreate, OrderRead
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