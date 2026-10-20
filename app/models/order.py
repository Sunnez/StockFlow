from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.order import OrderStatus

if TYPE_CHECKING:
    from app.models.order_item import OrderItem


CK_ORDERS_STATUS = "ck_orders_status"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(
            OrderStatus,
            name=CK_ORDERS_STATUS,
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
        default=OrderStatus.PENDING,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItem.position",
    )
