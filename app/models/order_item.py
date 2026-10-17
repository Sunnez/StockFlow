from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.order import Order


FK_ORDER_ITEMS_ORDER = "fk_order_items_order"
FK_ORDER_ITEMS_PRODUCT = "fk_order_items_product"
UQ_ORDER_ITEMS_ORDER_PRODUCT = "uq_order_items_order_product"
UQ_ORDER_ITEMS_ORDER_POSITION = "uq_order_items_order_position"
CK_ORDER_ITEMS_QUANTITY_POSITIVE = "ck_order_items_quantity_positive"
CK_ORDER_ITEMS_POSITION_POSITIVE = "ck_order_items_position_positive"


class OrderItem(Base):
    __tablename__ = "order_items"


    __table_args__ = (
        UniqueConstraint(
            "order_id",
            "product_id",
            name=UQ_ORDER_ITEMS_ORDER_PRODUCT,
        ),
        UniqueConstraint(
            "order_id",
            "position",
            name=UQ_ORDER_ITEMS_ORDER_POSITION,
        ),
        CheckConstraint(
            "quantity > 0",
            name=CK_ORDER_ITEMS_QUANTITY_POSITIVE,
        ),
        CheckConstraint(
            "position > 0",
            name=CK_ORDER_ITEMS_POSITION_POSITIVE,
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "orders.id",
            name=FK_ORDER_ITEMS_ORDER,
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    product_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "products.id",
            name=FK_ORDER_ITEMS_PRODUCT,
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        nullable=False
    )

    position: Mapped[int] = mapped_column(
        nullable=False,
    )

    order: Mapped[Order] = relationship(
        back_populates="items",
    )