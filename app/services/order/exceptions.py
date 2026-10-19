from uuid import UUID

from app.domain.order import OrderStatus
from app.core.exceptions import ApplicationValidationError, NotFoundError, ConflictError


class DuplicateProductInOrderError(ApplicationValidationError):
    def __init__(self, product_id: UUID):
        super().__init__(
            f"Product with id={product_id} already exists in order"
        )


class ProductsNotFoundInOrderError(NotFoundError):
    def __init__(self, product_ids: set[UUID]):
        self.product_ids = set(product_ids)
        ids = ", ".join(
            sorted(str(product_id) for product_id in self.product_ids)
        )
        super().__init__(
            f"Products with ids=[{ids}] do not exist"
        )


class EmptyOrderError(ApplicationValidationError):
    def __init__(self):
        super().__init__(
            "Order must contain at least one item"
        )


class OrderNotFoundError(NotFoundError):
    def __init__(self, order_id: UUID):
        super().__init__(
            f"Order with id={order_id} does not exist"
        )

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