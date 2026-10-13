class InventoryAlreadyExistsError(Exception):
    def __init__(
        self,
        product_id: int,
        warehouse_id: int,
    ):
        super().__init__(
            f"Product with id={product_id} already exists "
            f"in warehouse with id={warehouse_id}"
        )


class InventoryNotFoundError(Exception):
    def __init__(
        self,
        product_id: int,
        warehouse_id: int,
    ):
        super().__init__(
            f"Inventory for product id={product_id} "
            f"in warehouse id={warehouse_id} does not exist"
        )


class InvalidInventoryQuantityError(Exception):
    def __init__(self, quantity: int):
        super().__init__(
            f"Inventory quantity cannot be negative: {quantity}"
        )