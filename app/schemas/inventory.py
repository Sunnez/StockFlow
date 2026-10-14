from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InventoryCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(ge=0)

    model_config = ConfigDict(
        extra="forbid",
    )


class InventoryRead(BaseModel):
    id: UUID
    product_id: UUID
    warehouse_id: UUID
    quantity: int

    model_config = ConfigDict(
        from_attributes=True,
    )


class InventoryUpdate(BaseModel):
    quantity: int = Field(ge=0)

    model_config = ConfigDict(
        extra="forbid",
    )