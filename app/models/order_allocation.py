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

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.inventory import Inventory
    from app.models.order_item import OrderItem


FK_ORDER_ALLOCATION_ORDER_ITEM = "fk_order_allocation_order_item"
FK_ORDER_ALLOCATION_INVENTORY = "fk_order_allocation_inventory"
CK_ORDER_ALLOCATION_QUANTITY_GREATER_THAN_0 = "ck_order_allocation_quantity_greater_than_0"
UQ_ORDER_ALLOCATION_ORDER_ITEM_INVENTORY = "uq_order_allocation_order_item_inventory"
IX_ORDER_ALLOCATION_INVENTORY = "ix_order_allocation_inventory"

class OrderAllocation(Base):
    __tablename__ = "order_allocations"

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name=CK_ORDER_ALLOCATION_QUANTITY_GREATER_THAN_0,
        ),
        UniqueConstraint(
            "order_item_id",
            "inventory_id",
            name=UQ_ORDER_ALLOCATION_ORDER_ITEM_INVENTORY,
        ),
        Index(
            IX_ORDER_ALLOCATION_INVENTORY,
            "inventory_id",
        )
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    order_item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "order_items.id",
            name=FK_ORDER_ALLOCATION_ORDER_ITEM,
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    inventory_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "inventory.id",
            name=FK_ORDER_ALLOCATION_INVENTORY,
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        nullable=False,
    )

    order_item: Mapped[OrderItem] = relationship(
        back_populates="allocations",
    )

    inventory: Mapped[Inventory] = relationship(
        back_populates="allocations",
    )