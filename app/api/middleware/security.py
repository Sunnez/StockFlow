from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def trusted_request_source(origin: str | None, referer: str | None) -> bool:
    # An explicit Origin always takes precedence, including the opaque "null" origin.
    if origin is not None:
        return origin in settings.auth_allowed_origins
    if not referer:
        return False
    try:
        source = urlsplit(referer)
        if source.scheme not in {"http", "https"} or not source.hostname:
            return False
        if source.username is not None or source.password is not None:
            return False
        # Keep scheme, host and port exact. No suffix matching or automatic aliases.
        source_origin = f"{source.scheme}://{source.netloc}"
    except ValueError:
        return False
    return source_origin in settings.auth_allowed_origins


async def verify_request_origin(request: Request, call_next):
    if request.method not in SAFE_METHODS and not trusted_request_source(
        request.headers.get("origin"),
        request.headers.get("referer"),
    ):
        return JSONResponse(
            status_code=403,
            content={"detail": "A trusted Origin or Referer is required"},
        )
    return await call_next(request)
