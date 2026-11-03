"""Turns domain exceptions into HTTP responses so routers don't need try/except."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.common.exceptions import (
    DomainError,
    DomainValidationError,
    InsufficientInventoryError,
    InvalidStateTransitionError,
    NotFoundError,
)

# The most specific class in an exception's MRO wins. Later phases add entries here.
STATUS_BY_ERROR: dict[type[DomainError], int] = {
    DomainValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    NotFoundError: status.HTTP_404_NOT_FOUND,
    InsufficientInventoryError: status.HTTP_409_CONFLICT,
    InvalidStateTransitionError: status.HTTP_409_CONFLICT,
    DomainError: status.HTTP_400_BAD_REQUEST,
}


def status_for(error: DomainError) -> int:
    for cls in type(error).__mro__:
        if cls in STATUS_BY_ERROR:
            return STATUS_BY_ERROR[cls]
    return status.HTTP_400_BAD_REQUEST


async def _handle_domain_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    return JSONResponse(
        status_code=status_for(exc),
        content={"error": type(exc).__name__, "message": str(exc)},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _handle_domain_error)
