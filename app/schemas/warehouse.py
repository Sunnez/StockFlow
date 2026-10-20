from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class WarehouseUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    location: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    @model_validator(mode="after")
    def validate_update(self):
        if self.name is None and self.location is None:
            raise ValueError("At least one field must be provided")
        return self
