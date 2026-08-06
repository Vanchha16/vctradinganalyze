"""Phase 9A (ADR-132) - baseline security headers
(`app/middleware/security_headers.py`)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware import SecurityHeadersMiddleware


def _client() -> TestClient:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/ping")
    def _ping() -> dict[str, str]:
        return {"status": "ok"}

    return TestClient(app)


def test_response_includes_nosniff_header() -> None:
    response = _client().get("/ping")

    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_response_includes_frame_options_deny() -> None:
    response = _client().get("/ping")

    assert response.headers["X-Frame-Options"] == "DENY"


def test_response_includes_referrer_policy() -> None:
    response = _client().get("/ping")

    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_real_app_applies_the_middleware() -> None:
    """Proves `app/main.py` actually wires this in, not just that the
    middleware class works in isolation."""
    from app.main import app

    response = TestClient(app).get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
