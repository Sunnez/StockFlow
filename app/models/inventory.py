from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
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
CK_INVENTORY_RESERVED_QUANTITY_NON_NEGATIVE = "ck_inventory_reserved_quantity_non_negative"
CK_INVENTORY_RESERVED_NOT_GREATER_THAN_QUANTITY = "ck_inventory_reserved_not_greater_than_quantity"

FK_INVENTORY_PRODUCT = "fk_inventory_product"
FK_INVENTORY_WAREHOUSE = "fk_inventory_warehouse"

IX_INVENTORY_WAREHOUSE_ID = "ix_inventory_warehouse_id"


class Inventory(Base):
    __tablename__ = "inventory"

    __table_args__ = (
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

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    product_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "products.id",
            name=FK_INVENTORY_PRODUCT,
        ),
        nullable=False,
    )

    warehouse_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "warehouses.id",
            name=FK_INVENTORY_WAREHOUSE,
        ),
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
        passive_deletes=True,
    )

    @property
    def available_quantity(self) -> int:
        return self.quantity - self.reserved_quantity