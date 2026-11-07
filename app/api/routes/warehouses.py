from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.organization import BusinessReadContext, BusinessWriteContext
from app.db.session import get_db
from app.schemas.warehouse import WarehouseCreate, WarehouseRead, WarehouseUpdate
from app.services.warehouse import service as warehouse_service

router = APIRouter(
    prefix="/organizations/{organization_id}/warehouses",
    tags=["Warehouses"],
)


@router.post(
    "",
    response_model=WarehouseRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_warehouse(
    data: WarehouseCreate,
    org_context: BusinessWriteContext,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await warehouse_service.create_warehouse(
        db,
        organization_id=org_context.organization.id,
        actor_id=org_context.user.id,
        name=data.name,
        location=data.location,
    )


@router.get(
    "",
    response_model=list[WarehouseRead],
)
async def get_warehouses(
    org_context: BusinessReadContext,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return await warehouse_service.list_warehouses(
        db,
        organization_id=org_context.organization.id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{warehouse_id}",
    response_model=WarehouseRead,
)
async def get_warehouse(
    warehouse_id: UUID,
    org_context: BusinessReadContext,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await warehouse_service.get_warehouse(
        db,
        organization_id=org_context.organization.id,
        warehouse_id=warehouse_id,
    )


@router.patch(
    "/{warehouse_id}",
    response_model=WarehouseRead,
)
async def update_warehouse(
    warehouse_id: UUID,
    data: WarehouseUpdate,
    org_context: BusinessWriteContext,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await warehouse_service.update_warehouse(
        db,
        organization_id=org_context.organization.id,
        actor_id=org_context.user.id,
        warehouse_id=warehouse_id,
        name=data.name,
        location=data.location,
    )


@router.delete(
    "/{warehouse_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_warehouse(
    warehouse_id: UUID,
    org_context: BusinessWriteContext,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await warehouse_service.delete_warehouse(
        db,
        organization_id=org_context.organization.id,
        actor_id=org_context.user.id,
        warehouse_id=warehouse_id,
    )
