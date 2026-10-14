from uuid import UUID

from app.core.exceptions import (
    ApplicationValidationError,
    ConflictError,
    NotFoundError,
)


class InventoryAlreadyExistsError(ConflictError):
    def __init__(
        self,
        product_id: UUID,
        warehouse_id: UUID,
    ):
        super().__init__(
            f"Product with id={product_id} already exists "
            f"in warehouse with id={warehouse_id}"
        )


class InventoryNotFoundError(NotFoundError):
    def __init__(
        self,
        product_id: UUID,
        warehouse_id: UUID,
    ):
        super().__init__(
            f"Inventory for product id={product_id} "
            f"in warehouse id={warehouse_id} does not exist"
        )


class InvalidInventoryQuantityError(ApplicationValidationError):
    def __init__(self, quantity: int):
        super().__init__(
            f"Inventory quantity cannot be negative: {quantity}"
        )