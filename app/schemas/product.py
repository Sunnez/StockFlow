from pydantic import BaseModel, ConfigDict


class ProductCreate(BaseModel):
    name: str
    sku: str


class ProductRead(BaseModel):
    id: int
    name: str
    sku: str

    model_config = ConfigDict(from_attributes=True)