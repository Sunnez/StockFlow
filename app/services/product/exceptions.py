from uuid import UUID

from app.core.exceptions import ConflictError, NotFoundError, ApplicationValidationError


class ProductNotFoundError(NotFoundError):
    def __init__(self, product_id: UUID):
        super().__init__(
            f"Product with id={product_id} does not exist"
        )


class ProductSkuAlreadyExistsError(ConflictError):
    def __init__(self, sku: str):
        super().__init__(
            f"Product with sku='{sku}' already exists"
        )


class ProductUpdateError(ApplicationValidationError):
    def __init__(self, product_id: UUID):
        super().__init__(
            f"Product with id={product_id} name and sku are missing"
        )


class ProductUsedInOrderError(ConflictError):
    def __init__(self, product_id: UUID, order_id: UUID):
        super().__init__(
            f"Product with id={product_id} is used in order with id={order_id}"
        )


class ProductHasStockError(ConflictError):
    def __init__(self, product_id: UUID):
        super().__init__(
            f"Product with id={product_id} has stock in inventory"
        )