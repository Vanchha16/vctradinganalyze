from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline security headers on every response (Phase 9A, ADR-132).

    A full `Content-Security-Policy` is deliberately NOT included here -
    Next.js requires careful CSP work (inline styles, hydration) and a
    wrong policy silently breaks the app in the browser without failing
    any backend test. Recorded as remaining open in BACKLOG.md §4.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
