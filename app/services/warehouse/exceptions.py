from uuid import UUID

from app.core.exceptions import ConflictError, NotFoundError


class WarehouseNotFoundError(NotFoundError):
    def __init__(self, warehouse_id: UUID):
        super().__init__(
            f"Warehouse with id={warehouse_id} does not exist"
        )


class WarehouseNameAlreadyExistsError(ConflictError):
    def __init__(self, name: str):
        super().__init__(
            f"Warehouse with name='{name}' already exists"
        )