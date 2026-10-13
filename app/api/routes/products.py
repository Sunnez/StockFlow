from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductRead

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
    product = Product(
        name=data.name,
        sku=data.sku,
    )

    db.add(product)

    await db.commit()
    await db.refresh(product)

    return product


@router.get(
    "",
    response_model=list[ProductRead]
)
async def get_products(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product)
    )

    return result.scalars().all()


@router.get(
    "/{product_id}",
    response_model=ProductRead
)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return product