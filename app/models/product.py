from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

UQ_PRODUCTS_SKU = "uq_products_organization_sku"


class Product(Base):
    __tablename__ = "products"

    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_products_organization_id"),
        UniqueConstraint(
            "organization_id",
            "sku",
            name=UQ_PRODUCTS_SKU,
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "organizations.id", name="fk_products_organization", ondelete="RESTRICT"
        ),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    sku: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
