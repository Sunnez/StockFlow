from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrderAllocationRead(BaseModel):
    id: UUID
    inventory_id: UUID
    quantity: int

    model_config = ConfigDict(
        from_attributes=True,
    )