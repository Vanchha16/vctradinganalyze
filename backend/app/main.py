from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from app.api.v1.router import api_router
from app.config import settings
from app.core.logging import configure_logging
from app.exceptions import register_exception_handlers
from app.middleware import CorrelationIdMiddleware, MetricsMiddleware, SecurityHeadersMiddleware
from app.services import runtime_settings
from app.services.ingestion_health import log_active_providers


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    configure_logging(settings.log_level)
    # Phase 9G (ADR-139) - mock provider usage must never be silently
    # discovered later; log it once at startup.
    log_active_providers()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url=f"{settings.api_v1_prefix}/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    # Phase 9A (ADR-132) - scoped down from allow-everything (flagged
    # since before Phase 1.1, BACKLOG §4). `frontend/services/api-client.ts`
    # is the only caller and never sends cookies (`fetch()` there has no
    # `credentials: "include"`, so nothing cross-origin was ever actually
    # relying on this) - it authenticates via a bearer token in the
    # `Authorization` header instead, so `allow_credentials=True` was
    # dead weight, not a real requirement.
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(MetricsMiddleware)


@app.middleware("http")
async def _refresh_runtime_settings(request: Request, call_next):  # type: ignore[no-untyped-def]
    """ADR-178 - pick up settings the super admin changed. Cached for 30s and
    fail-open inside `refresh`; run in a thread so its occasional database
    read never blocks the event loop."""
    await run_in_threadpool(runtime_settings.refresh)
    return await call_next(request)


register_exception_handlers(app)

app.include_router(api_router, prefix=settings.api_v1_prefix)
