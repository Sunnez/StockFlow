from uuid import UUID

from app.core.exceptions import ApplicationValidationError, ConflictError, NotFoundError
from app.domain.order import OrderStatus


class DuplicateProductInOrderError(ApplicationValidationError):
    def __init__(self, product_id: UUID):
        super().__init__(f"Product with id={product_id} already exists in order")


class ProductsNotFoundInOrderError(NotFoundError):
    def __init__(self, product_ids: set[UUID]):
        self.product_ids = set(product_ids)
        ids = ", ".join(sorted(str(product_id) for product_id in self.product_ids))
        super().__init__(f"Products with ids=[{ids}] do not exist")


class EmptyOrderError(ApplicationValidationError):
    def __init__(self):
        super().__init__("Order must contain at least one item")


class OrderNotFoundError(NotFoundError):
    def __init__(self, order_id: UUID):
        super().__init__(f"Order with id={order_id} does not exist")


class OrderCannotBeUpdatedError(ConflictError):
    def __init__(self, order_id: UUID, order_status: OrderStatus):
        super().__init__(
            f"Order with id={order_id} cannot be updated while status is '{order_status}'"
        )


class OrderCannotBeDeletedError(ConflictError):
    def __init__(self, order_id: UUID, order_status: OrderStatus):
        super().__init__(
            f"Order with id={order_id} cannot be deleted while status is '{order_status}'"
        )


class OrderCannotBeAllocatedError(ConflictError):
    def __init__(self, order_id: UUID, order_status: OrderStatus):
        super().__init__(
            f"Order with id={order_id} cannot be allocated while status is {order_status}"
        )


class InsufficientInventoryError(ConflictError):
    def __init__(
        self, product_id: UUID, requested_quantity: int, available_quantity: int
    ):
        super().__init__(
            f"Insufficient inventory for product id={product_id}: "
            f"requested={requested_quantity}, "
            f"available={available_quantity}"
        )


class OrderCannotBeFulfilledError(ConflictError):
    def __init__(self, order_id: UUID, order_status: OrderStatus):
        super().__init__(
            f"Order with id={order_id} cannot be fulfilled while status is {order_status}"
        )


class InventoryReservationMismatchError(ConflictError):
    def __init__(
        self,
        inventory_id: UUID,
        allocation_quantity: int,
        quantity: int,
        reserved_quantity: int,
    ):
        super().__init__(
            f"Inventory id={inventory_id} cannot fulfill allocation "
            f"quantity={allocation_quantity}: "
            f"quantity={quantity}, "
            f"reserved_quantity={reserved_quantity}"
        )


class OrderCannotBeCancelledError(ConflictError):
    def __init__(self, order_id: UUID, order_status: OrderStatus):
        super().__init__(
            f"Order with id={order_id} cannot be cancelled "
            f"while status is '{order_status}'"
        )
