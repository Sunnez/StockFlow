from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.order import OrderStatus
from app.schemas.order_item import OrderItemCreate, OrderItemRead


class OrderCreate(BaseModel):
    items: list[OrderItemCreate] = Field(min_length=1)

    model_config = ConfigDict(
        extra='forbid',
    )

class OrderRead(BaseModel):
    id: UUID
    status: OrderStatus
    created_at: datetime
    items: list[OrderItemRead]

    model_config = ConfigDict(
        from_attributes=True,
    )

class OrderUpdate(BaseModel):
    items: list[OrderItemCreate] = Field(min_length=1)

    model_config = ConfigDict(
        extra="forbid",
    )