from uuid import UUID, uuid4

from sqlalchemy import String, UniqueConstraint, Uuid
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

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    sku: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
