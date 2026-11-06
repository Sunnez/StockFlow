from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    ApplicationValidationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)


def _error_response(
    *,
    status_code: int,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": str(exc),
        },
    )


async def not_found_handler(
    _request: Request,
    exc: NotFoundError,
) -> JSONResponse:
    return _error_response(
        status_code=status.HTTP_404_NOT_FOUND,
        exc=exc,
    )


async def conflict_handler(
    _request: Request,
    exc: ConflictError,
) -> JSONResponse:
    return _error_response(
        status_code=status.HTTP_409_CONFLICT,
        exc=exc,
    )


async def application_validation_handler(
    _request: Request,
    exc: ApplicationValidationError,
) -> JSONResponse:
    return _error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        exc=exc,
    )


async def unauthorized_handler(
    _request: Request,
    exc: UnauthorizedError,
) -> JSONResponse:
    return _error_response(
        status_code=status.HTTP_401_UNAUTHORIZED,
        exc=exc,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        NotFoundError,
        not_found_handler,
    )

    app.add_exception_handler(
        ConflictError,
        conflict_handler,
    )

    app.add_exception_handler(
        ApplicationValidationError,
        application_validation_handler,
    )

    app.add_exception_handler(
        UnauthorizedError,
        unauthorized_handler,
    )

    app.add_exception_handler(
    ForbiddenError,
    forbidden_handler,
    )


async def forbidden_handler(
    _request: Request,
    exc: ForbiddenError,
) -> JSONResponse:
    return _error_response(
        status_code=status.HTTP_403_FORBIDDEN,
        exc=exc,
    )