"""Structured error responses (docs/api-standards.md, NFR-MAIN-01, NFR-REL-02).

Every error leaves the API in the same envelope:

    {"error": {"code": "validation_error", "message": "...", "details": [...]}}

Unexpected exceptions are logged server-side and returned as a generic 500 so that
implementation details never reach the client.
"""

import logging
from http import HTTPStatus
from typing import Any, ClassVar

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for expected, client-facing errors raised by services."""

    status_code: int = HTTPStatus.BAD_REQUEST
    code: str = "bad_request"
    headers: ClassVar[dict[str, str] | None] = None

    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class UnauthorizedError(AppError):
    """Missing, invalid or expired credentials (FR-AUTH-02)."""

    status_code = HTTPStatus.UNAUTHORIZED
    code = "unauthorized"
    headers: ClassVar[dict[str, str] | None] = {"WWW-Authenticate": "Bearer"}


class ForbiddenError(AppError):
    """Authenticated, but the user's roles do not grant the permission (FR-AUTH-03)."""

    status_code = HTTPStatus.FORBIDDEN
    code = "forbidden"


class NotFoundError(AppError):
    status_code = HTTPStatus.NOT_FOUND
    code = "not_found"


class ConflictError(AppError):
    status_code = HTTPStatus.CONFLICT
    code = "conflict"


class BusinessRuleError(AppError):
    """A request that is well-formed but violates a business rule (BR-*)."""

    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    code = "business_rule_violation"


def error_body(code: str, message: str, details: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        error_body(exc.code, exc.message, exc.details), status_code=exc.status_code, headers=exc.headers
    )


async def _http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    status = HTTPStatus(exc.status_code)
    code = status.phrase.lower().replace(" ", "_")
    message = exc.detail if isinstance(exc.detail, str) else status.phrase
    return JSONResponse(error_body(code, message), status_code=exc.status_code, headers=exc.headers)


async def _validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {"field": ".".join(str(part) for part in err["loc"]), "message": err["msg"], "type": err["type"]}
        for err in exc.errors()
    ]
    return JSONResponse(
        error_body("validation_error", "Request validation failed.", details),
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
    )


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        error_body("internal_error", "An unexpected error occurred."),
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
    )


def register_error_handlers(app: FastAPI) -> None:
    app.exception_handler(AppError)(_app_error_handler)
    app.exception_handler(StarletteHTTPException)(_http_error_handler)
    app.exception_handler(RequestValidationError)(_validation_error_handler)
    app.exception_handler(Exception)(_unhandled_error_handler)
