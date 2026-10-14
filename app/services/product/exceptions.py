from uuid import UUID

from app.core.exceptions import ConflictError, NotFoundError


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