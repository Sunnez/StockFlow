from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.warehouse import WarehouseCreate, WarehouseRead, WarehouseUpdate
from app.services.warehouse import service as warehouse_service


router = APIRouter(
    prefix="/warehouses",
    tags=["Warehouses"],
)


@router.post(
    "",
    response_model=WarehouseRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_warehouse(
    data: WarehouseCreate,
    db: AsyncSession = Depends(get_db),
):
    return await warehouse_service.create_warehouse(
        db,
        name=data.name,
        location=data.location,
    )


@router.get(
    "",
    response_model=list[WarehouseRead],
)
async def get_warehouses(
    db: AsyncSession = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return await warehouse_service.list_warehouses(
        db,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{warehouse_id}",
    response_model=WarehouseRead,
)
async def get_warehouse(
    warehouse_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await warehouse_service.get_warehouse(
        db,
        warehouse_id=warehouse_id,
    )


@router.patch(
    "/{warehouse_id}",
    response_model=WarehouseRead,
)
async def update_warehouse(
    warehouse_id: UUID,
    data: WarehouseUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await warehouse_service.update_warehouse(
        db,
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
    db: AsyncSession = Depends(get_db),
):
    await warehouse_service.delete_warehouse(
        db,
        warehouse_id=warehouse_id,
    )
