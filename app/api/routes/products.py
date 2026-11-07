from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.organization import BusinessReadContext, BusinessWriteContext
from app.db.session import get_db
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.product import service as product_service

router = APIRouter(
    prefix="/organizations/{organization_id}/products",
    tags=["Products"],
)


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    data: ProductCreate,
    org_context: BusinessWriteContext,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await product_service.create_product(
        db,
        organization_id=org_context.organization.id,
        actor_id=org_context.user.id,
        name=data.name,
        sku=data.sku,
    )


@router.get(
    "",
    response_model=list[ProductRead],
)
async def list_products(
    org_context: BusinessReadContext,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return await product_service.list_products(
        db,
        organization_id=org_context.organization.id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{product_id}",
    response_model=ProductRead,
)
async def get_product(
    product_id: UUID,
    org_context: BusinessReadContext,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await product_service.get_product(
        db,
        organization_id=org_context.organization.id,
        product_id=product_id,
    )


@router.patch(
    "/{product_id}",
    response_model=ProductRead,
)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    org_context: BusinessWriteContext,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await product_service.update_product(
        db,
        organization_id=org_context.organization.id,
        actor_id=org_context.user.id,
        product_id=product_id,
        name=data.name,
        sku=data.sku,
    )


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_product(
    product_id: UUID,
    org_context: BusinessWriteContext,
    db: Annotated[AsyncSession, Depends(get_db)],
):

    await product_service.delete_product(
        db,
        organization_id=org_context.organization.id,
        actor_id=org_context.user.id,
        product_id=product_id,
    )
