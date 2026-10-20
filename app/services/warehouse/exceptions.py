from uuid import UUID

from app.core.exceptions import ConflictError, NotFoundError, ApplicationValidationError


class WarehouseNotFoundError(NotFoundError):
    def __init__(self, warehouse_id: UUID):
        super().__init__(f"Warehouse with id={warehouse_id} does not exist")


class WarehouseNameAlreadyExistsError(ConflictError):
    def __init__(self, name: str):
        super().__init__(f"Warehouse with name='{name}' already exists")


class WarehouseUpdateError(ApplicationValidationError):
    def __init__(self, warehouse_id: UUID):
        super().__init__(
            f"Warehouse with id={warehouse_id} name and location are missing"
        )


class WarehouseHasInventoryError(ConflictError):
    def __init__(self, warehouse_id: UUID):
        super().__init__(
            f"Warehouse with id={warehouse_id} cannot be deleted "
            f"because it has inventory entries"
        )
