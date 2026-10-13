from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.services.inventory.exceptions import (
    InventoryAlreadyExistsError,
    InventoryNotFoundError,
    InvalidInventoryQuantityError,
)
from app.services.product.exceptions import (
    ProductNotFoundError,
    ProductSkuAlreadyExistsError,
)
from app.services.warehouse.exceptions import (
    WarehouseNameAlreadyExistsError,
    WarehouseNotFoundError,
)


async def not_found_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": str(exc),
        },
    )


async def conflict_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": str(exc),
        },
    )


async def validation_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": str(exc),
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        ProductNotFoundError,
        not_found_handler,
    )
    app.add_exception_handler(
        WarehouseNotFoundError,
        not_found_handler,
    )
    app.add_exception_handler(
        InventoryNotFoundError,
        not_found_handler,
    )

    app.add_exception_handler(
        ProductSkuAlreadyExistsError,
        conflict_handler,
    )
    app.add_exception_handler(
        WarehouseNameAlreadyExistsError,
        conflict_handler,
    )
    app.add_exception_handler(
        InventoryAlreadyExistsError,
        conflict_handler,
    )

    app.add_exception_handler(
        InvalidInventoryQuantityError,
        validation_handler,
    )