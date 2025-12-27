from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, *, status_code: int, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details

    @staticmethod
    def bad_request(message: str, details: Optional[Dict[str, Any]] = None) -> "AppError":
        return AppError(status_code=400, code="bad_request", message=message, details=details)

    @staticmethod
    def unauthorized(message: str, details: Optional[Dict[str, Any]] = None) -> "AppError":
        return AppError(status_code=401, code="unauthorized", message=message, details=details)

    @staticmethod
    def forbidden(message: str, details: Optional[Dict[str, Any]] = None) -> "AppError":
        return AppError(status_code=403, code="forbidden", message=message, details=details)

    @staticmethod
    def not_found(message: str, details: Optional[Dict[str, Any]] = None) -> "AppError":
        return AppError(status_code=404, code="not_found", message=message, details=details)

    @staticmethod
    def conflict(message: str, details: Optional[Dict[str, Any]] = None) -> "AppError":
        return AppError(status_code=409, code="conflict", message=message, details=details)


def _envelope(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    err: Dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        err["details"] = details
    return {"error": err}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_envelope(exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=_envelope(
                "bad_request",
                "invalid payload",
                details={"errors": exc.errors()},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exc_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        status = exc.status_code
        if status == 401:
            code = "unauthorized"
        elif status == 403:
            code = "forbidden"
        elif status == 404:
            code = "not_found"
        elif status == 409:
            code = "conflict"
        else:
            code = "bad_request"
        return JSONResponse(status_code=status, content=_envelope(code, exc.detail))
