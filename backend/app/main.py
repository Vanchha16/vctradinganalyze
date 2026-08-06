from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import settings
from app.core.logging import configure_logging
from app.exceptions import register_exception_handlers
from app.middleware import CorrelationIdMiddleware, SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    configure_logging(settings.log_level)
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

register_exception_handlers(app)

app.include_router(api_router, prefix=settings.api_v1_prefix)
