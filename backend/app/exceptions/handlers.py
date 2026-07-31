import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions.base import AppException

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def handle_app_exception(_: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.error_code, "message": exc.message},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Normalize FastAPI's built-in validation-error shape
        (`{"detail": [...]}`) to the project's standard `{"error",
        "message"}` envelope (docs/04/docs/33 "Standard Response").

        Without this, an invalid query parameter (e.g. a bad `timeframe`)
        would return a differently-shaped error than every other failure
        in the API - a gap that existed since Phase 2C but only became
        visible once a phase had meaningfully-validated query parameters
        (Phase 3C).
        """
        first_error = exc.errors()[0] if exc.errors() else {}
        location = ".".join(str(part) for part in first_error.get("loc", []))
        message = first_error.get("msg", "Invalid request.")
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": f"{location}: {message}" if location else message,
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "An unexpected error occurred."},
        )
