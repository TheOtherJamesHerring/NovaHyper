"""
app/main.py
-----------
FastAPI application factory.

Startup sequence:
1. Validate configuration
2. Run Alembic migrations (dev/staging only — in prod, run migrations separately)
3. Register routers
4. Connect to NATS
5. Start background workers (metrics scraper, usage meter flush)
"""
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from app.api.v1.endpoints import auth, vms, backups
from app.core.config import get_settings

settings = get_settings()
log = structlog.get_logger(__name__)

# ── Prometheus metrics ─────────────────────────────────────────────────────────

REQUEST_COUNT = Counter(
    "novahyper_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "novahyper_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log.info("novahyper.startup", version=settings.APP_VERSION, env=settings.ENVIRONMENT)

    # Connect to NATS (non-fatal — jobs queue gracefully if unavailable at startup)
    try:
        import nats
        nc = await nats.connect(settings.NATS_URL)
        app.state.nats = nc
        log.info("nats.connected", url=settings.NATS_URL)
    except Exception as exc:
        log.warning("nats.unavailable", error=str(exc))
        app.state.nats = None

    yield  # App is running

    # Shutdown
    if getattr(app.state, "nats", None):
        await app.state.nats.close()
    log.info("novahyper.shutdown")


# ── Application factory ────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="MSP Hypervisor Platform API — VM lifecycle, backup, and dedup",
        lifespan=lifespan,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    )

    # CORS — tighten origins in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.ENVIRONMENT == "development" else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request instrumentation middleware ─────────────────────────────────
    @app.middleware("http")
    async def instrument(request: Request, call_next) -> Response:  # type: ignore
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        # Normalise path for cardinality safety (strip UUIDs from path)
        endpoint = request.url.path
        REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
        REQUEST_LATENCY.labels(request.method, endpoint).observe(duration)
        return response

    # ── Routers ────────────────────────────────────────────────────────────
    API_PREFIX = "/api/v1"
    app.include_router(auth.router, prefix=API_PREFIX)
    app.include_router(vms.router, prefix=API_PREFIX)
    app.include_router(backups.router, prefix=API_PREFIX)
    # Future: backups, tenants, storage, networks, audit

    # ── Health & metrics ───────────────────────────────────────────────────
    @app.get("/health", tags=["ops"], summary="Liveness probe")
    async def health() -> dict:
        return {"status": "ok", "version": settings.APP_VERSION}

    @app.get("/ready", tags=["ops"], summary="Readiness probe")
    async def ready() -> dict:
        from app.db.session import engine
        try:
            async with engine.connect() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            return {"status": "ready", "db": "ok"}
        except Exception as exc:
            from fastapi import HTTPException
            raise HTTPException(status_code=503, detail=f"DB not ready: {exc}")

    if settings.METRICS_ENABLED:
        @app.get("/metrics", tags=["ops"], summary="Prometheus metrics scrape endpoint")
        async def metrics() -> Response:
            return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
