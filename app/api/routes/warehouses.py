from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.warehouse import Warehouse
from app.schemas.warehouse import WarehouseCreate, WarehouseRead


router = APIRouter(
    prefix="/warehouses",
    tags=["Warehouses"],
)


@router.post(
    "",
    response_model=WarehouseRead,
    status_code=status.HTTP_201_CREATED,
)
async def warehouse_create(data: WarehouseCreate, db: AsyncSession = Depends(get_db)):
    warehouse = Warehouse(name=data.name, location=data.location)

    db.add(warehouse)

    await db.commit()
    await db.refresh(warehouse)

    return warehouse


@router.get(
    "",
    response_model=WarehouseRead
)
async def get_warehouses(
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Warehouse)
    )

    return result.scalars().all()


@router.get(
    "/{warehouse_id}",
    response_model=WarehouseRead
)
async def get_warehouse(
    warehouse_id: int,
    db: AsyncSession = Depends(get_db)
):
    warehouse = await db.get(Warehouse, warehouse_id)

    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Warehouse not found'
        )

    return warehouse