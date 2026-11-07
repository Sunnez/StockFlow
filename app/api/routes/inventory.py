from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.organization import BusinessReadContext, BusinessWriteContext
from app.db.session import get_db
from app.schemas.inventory import (
    InventoryCreate,
    InventoryRead,
    InventoryUpdate,
)
from app.services.inventory import service as inventory_service

router = APIRouter(
    prefix="/organizations/{organization_id}/warehouses",
    tags=["Inventory"],
)


@router.post(
    "/{warehouse_id}/inventory",
    response_model=InventoryRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_inventory(
    warehouse_id: UUID,
    data: InventoryCreate,
    org_context: BusinessWriteContext,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await inventory_service.create_inventory(
        db,
        organization_id=org_context.organization.id,
        actor_id=org_context.user.id,
        warehouse_id=warehouse_id,
        product_id=data.product_id,
        quantity=data.quantity,
    )


@router.get(
    "/{warehouse_id}/inventory",
    response_model=list[InventoryRead],
)
async def get_warehouse_inventory(
    warehouse_id: UUID,
    org_context: BusinessReadContext,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return await inventory_service.list_warehouse_inventory(
        db,
        organization_id=org_context.organization.id,
        warehouse_id=warehouse_id,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/{warehouse_id}/inventory/{product_id}",
    response_model=InventoryRead,
)
async def update_inventory(
    warehouse_id: UUID,
    product_id: UUID,
    data: InventoryUpdate,
    org_context: BusinessWriteContext,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await inventory_service.update_inventory_quantity(
        db,
        organization_id=org_context.organization.id,
        actor_id=org_context.user.id,
        warehouse_id=warehouse_id,
        product_id=product_id,
        quantity=data.quantity,
    )


@router.delete(
    "/{warehouse_id}/inventory/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_inventory(
    warehouse_id: UUID,
    product_id: UUID,
    org_context: BusinessWriteContext,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await inventory_service.delete_inventory(
        db,
        organization_id=org_context.organization.id,
        actor_id=org_context.user.id,
        warehouse_id=warehouse_id,
        product_id=product_id,
    )
