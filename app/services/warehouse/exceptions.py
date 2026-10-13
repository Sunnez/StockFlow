class WarehouseNotFoundError(Exception):
    def __init__(self, warehouse_id: int):
        super().__init__(
            f"Warehouse with id={warehouse_id} does not exist"
        )


class WarehouseNameAlreadyExistsError(Exception):
    def __init__(self, name: str):
        super().__init__(
            f"Warehouse with name='{name}' already exists"
        )