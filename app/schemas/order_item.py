from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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

    model_config = ConfigDict(
        from_attributes=True,
    )