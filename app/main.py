from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import register_exception_handlers
from app.api.middleware.security import verify_request_origin
from app.api.routes.auth import router as auth_router
from app.api.routes.inventory import router as inventory_router
from app.api.routes.orders import router as orders_router
from app.api.routes.organizations import router as organizations_router
from app.api.routes.products import router as products_router
from app.api.routes.users import router as users_router
from app.api.routes.warehouses import router as warehouses_router
from app.core.config import settings

app = FastAPI(
    title="StockFlow",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.auth_allowed_origins,
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
    ],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-CSRF-Token",
    ],
)


@app.middleware("http")
async def security_middleware(
    request: Request,
    call_next,
):
    return await verify_request_origin(
        request,
        call_next,
    )


register_exception_handlers(app)

app.include_router(products_router)
app.include_router(warehouses_router)
app.include_router(inventory_router)
app.include_router(orders_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(organizations_router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
    }
