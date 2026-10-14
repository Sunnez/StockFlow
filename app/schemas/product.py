from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=255,
    )
    sku: str = Field(
        min_length=1,
        max_length=100,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )


class ProductRead(BaseModel):
    id: UUID
    name: str
    sku: str

    model_config = ConfigDict(
        from_attributes=True,
    )