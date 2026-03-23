"""Application middleware helpers."""

from __future__ import annotations

import time

import structlog
from fastapi import FastAPI, Request, Response

from app.core.security import decode_token

log = structlog.get_logger(__name__)
_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def register_mutating_request_log_middleware(app: FastAPI) -> None:
    """Log mutating HTTP requests for observability (not compliance audit)."""

    @app.middleware("http")
    async def log_mutations(request: Request, call_next) -> Response:  # type: ignore
        start = time.perf_counter()
        response = await call_next(request)

        if request.method in _MUTATING_METHODS:
            user_id = None
            tenant_id = None
            auth_header = request.headers.get("authorization", "")
            if auth_header.lower().startswith("bearer "):
                token = auth_header.split(" ", 1)[1].strip()
                try:
                    claims = decode_token(token)
                    user_id = claims.get("sub")
                    tenant_id = claims.get("tenant_id")
                except Exception:
                    pass

            duration_ms = (time.perf_counter() - start) * 1000
            client_ip = request.client.host if request.client is not None else None
            log.info(
                "http.mutating_request",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                user_id=user_id,
                tenant_id=tenant_id,
                ip_address=client_ip,
                duration_ms=round(duration_ms, 2),
            )

        return response
