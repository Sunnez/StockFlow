from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.order_allocation import OrderAllocationRead


class OrderItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0)

    model_config = ConfigDict(
        extra="forbid",
    )


class OrderItemRead(BaseModel):
    id: UUID
    product_id: UUID
    quantity: int
    allocations: list[OrderAllocationRead]

    model_config = ConfigDict(
        from_attributes=True,
    )