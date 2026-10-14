from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WarehouseCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=255,
    )
    location: str = Field(
        min_length=1,
        max_length=255,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )


class WarehouseRead(BaseModel):
    id: UUID
    name: str
    location: str

    model_config = ConfigDict(
        from_attributes=True,
    )