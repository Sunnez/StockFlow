class ProductNotFoundError(Exception):
    def __init__(self, product_id: int):
        super().__init__(
            f"Product with id={product_id} does not exist"
        )


class ProductSkuAlreadyExistsError(Exception):
    def __init__(self, sku: str):
        super().__init__(
            f"Product with sku='{sku}' already exists"
        )