import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_CORRELATION_ID_HEADER = "X-Correlation-ID"


def get_correlation_id() -> str:
    return str(structlog.contextvars.get_contextvars().get("correlation_id", ""))


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Assigns a correlation ID to every request for log tracing."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get(_CORRELATION_ID_HEADER, str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers[_CORRELATION_ID_HEADER] = correlation_id
        return response
