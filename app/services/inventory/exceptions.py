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
        super().__init__(f"Inventory quantity cannot be negative: {quantity}")


class InventoryNotEmptyError(ConflictError):
    def __init__(self, product_id: UUID, warehouse_id: UUID):
        super().__init__(
            f"Inventory for product id={product_id} "
            f"in warehouse id={warehouse_id} cannot be deleted since it is not empty"
        )


class InventoryQuantityBelowReservedError(ConflictError):
    def __init__(
        self,
        product_id: UUID,
        warehouse_id: UUID,
        quantity: int,
        reserved_quantity: int,
    ):
        super().__init__(
            f"Inventory quantity for product id={product_id} "
            f"in warehouse id={warehouse_id} cannot be set to {quantity} "
            f"because {reserved_quantity} units are reserved"
        )


class InventoryUsedInAllocationError(ConflictError):
    def __init__(self, product_id: UUID, warehouse_id: UUID):
        super().__init__(
            f"Inventory for product id={product_id} "
            f"in warehouse id={warehouse_id} cannot be deleted "
            f"because it is used in an order allocation"
        )
