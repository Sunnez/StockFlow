from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings

SAFE_METHODS = frozenset({
    "GET",
    "HEAD",
    "OPTIONS",
})


async def verify_request_origin(
    request: Request,
    call_next,
):
    if request.method not in SAFE_METHODS:
        origin = request.headers.get("origin")

        if origin not in settings.auth_allowed_origins:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Untrusted request origin",
                },
            )

    return await call_next(request)