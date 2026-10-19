from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class ProductUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    sku: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    @model_validator(mode="after")
    def validate_update(self):
        if self.name is None and self.sku is None:
            raise ValueError(
                "At least one field must be provided"
            )

        return self