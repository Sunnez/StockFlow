from fastapi import FastAPI

from app.api.exception_handlers import register_exception_handlers
from app.api.routes.inventory import router as inventory_router
from app.api.routes.orders import router as orders_router
from app.api.routes.products import router as products_router
from app.api.routes.warehouses import router as warehouses_router

app = FastAPI(
    title="StockFlow",
    version="0.1.0",
)

register_exception_handlers(app)

app.include_router(products_router)
app.include_router(warehouses_router)
app.include_router(inventory_router)
app.include_router(orders_router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
    }