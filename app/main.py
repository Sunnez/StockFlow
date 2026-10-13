from fastapi import FastAPI

from app.api.routes.products import router as products_router
from app.api.routes.warehouses import router as warehouses_router

app = FastAPI(
    title="StockFlow",
    version="0.1.0",
)

app.include_router(products_router)
app.include_router(warehouses_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}