from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.order_allocation import OrderAllocation

from app.db.base import Base

UQ_INVENTORY_PRODUCT_WAREHOUSE = "uq_inventory_product_warehouse"
CK_INVENTORY_QUANTITY_NON_NEGATIVE = "ck_inventory_quantity_non_negative"
CK_INVENTORY_RESERVED_QUANTITY_NON_NEGATIVE = (
    "ck_inventory_reserved_quantity_non_negative"
)
CK_INVENTORY_RESERVED_NOT_GREATER_THAN_QUANTITY = (
    "ck_inventory_reserved_not_greater_than_quantity"
)

FK_INVENTORY_PRODUCT = "fk_inventory_product"
FK_INVENTORY_WAREHOUSE = "fk_inventory_warehouse"

IX_INVENTORY_WAREHOUSE_ID = "ix_inventory_warehouse_id"


class Inventory(Base):
    __tablename__ = "inventory"

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "id",
            "product_id",
            name="uq_inventory_organization_id_product",
        ),
        ForeignKeyConstraint(
            ["organization_id", "product_id"],
            ["products.organization_id", "products.id"],
            name=FK_INVENTORY_PRODUCT,
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "warehouse_id"],
            ["warehouses.organization_id", "warehouses.id"],
            name=FK_INVENTORY_WAREHOUSE,
            ondelete="RESTRICT",
        ),
        Index(
            "ix_inventory_organization_product_lock",
            "organization_id",
            "product_id",
            "warehouse_id",
            "id",
        ),
        Index(
            "ix_inventory_organization_warehouse_id",
            "organization_id",
            "warehouse_id",
            "id",
        ),
        UniqueConstraint(
            "product_id",
            "warehouse_id",
            name=UQ_INVENTORY_PRODUCT_WAREHOUSE,
        ),
        CheckConstraint(
            "quantity >= 0",
            name=CK_INVENTORY_QUANTITY_NON_NEGATIVE,
        ),
        CheckConstraint(
            "reserved_quantity >= 0",
            name=CK_INVENTORY_RESERVED_QUANTITY_NON_NEGATIVE,
        ),
        CheckConstraint(
            "reserved_quantity <= quantity",
            name=CK_INVENTORY_RESERVED_NOT_GREATER_THAN_QUANTITY,
        ),
        Index(
            IX_INVENTORY_WAREHOUSE_ID,
            "warehouse_id",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    product_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )

    warehouse_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        nullable=False,
    )

    reserved_quantity: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default="0",
    )

    allocations: Mapped[list[OrderAllocation]] = relationship(
        back_populates="inventory",
        foreign_keys="OrderAllocation.inventory_id",
        passive_deletes=True,
    )

    @property
    def available_quantity(self) -> int:
        return self.quantity - self.reserved_quantity
