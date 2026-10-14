from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.product import ProductCreate, ProductRead
from app.services.product import service as product_service


router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
):
    return await product_service.create_product(
        db,
        name=data.name,
        sku=data.sku,
    )


@router.get(
    "",
    response_model=list[ProductRead],
)
async def get_products(
    db: AsyncSession = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return await product_service.list_products(
        db,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{product_id}",
    response_model=ProductRead,
)
async def get_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await product_service.get_product(
        db,
        product_id=product_id,
    )