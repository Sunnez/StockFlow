from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


UQ_PRODUCTS_SKU = "uq_products_sku"


class Product(Base):
    __tablename__ = "products"

    __table_args__ = (
        UniqueConstraint(
            "sku",
            name=UQ_PRODUCTS_SKU,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    sku: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )