from pydantic import BaseModel, ConfigDict


class WarehouseCreate(BaseModel):
    name: str
    location: str


class WarehouseRead(BaseModel):
    id: int
    name: str
    location: str

    model_config = ConfigDict(from_attributes=True)