"""Audit writer service for immutable business event logging."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import Request

from app.models import AuditLog, User

SUPPORTED_AUDIT_ACTIONS = {
    "vm.create",
    "vm.delete",
    "vm.action",
    "backup.create",
    "backup.cancel",
    "backup.delete",
    "tenant.create",
    "tenant.update",
    "tenant.suspend",
    "tenant.reinstate",
    "tenant.delete",
    "user.create",
    "user.role_change",
    "auth.login",
    "auth.login_failed",
}


def payload_sha256(payload: dict[str, Any]) -> str:
    """Return a deterministic SHA-256 hex digest for a JSON payload."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip() or None
    if request.client is None:
        return None
    return request.client.host


async def write_audit_event(
    db: Any,
    request: Request,
    user: User | None,
    action: str,
    resource_type: str,
    resource_id: str | None,
    payload: dict[str, Any],
) -> AuditLog:
    """Write one immutable audit event in the active database transaction."""
    if action not in SUPPORTED_AUDIT_ACTIONS:
        raise ValueError(f"Unsupported audit action: {action}")

    tenant_id = payload.get("tenant_id")
    user_id = payload.get("user_id")

    event = AuditLog(
        id=str(uuid.uuid4()),
        tenant_id=str(tenant_id) if tenant_id is not None else (str(user.tenant_id) if user is not None and user.tenant_id is not None else None),
        user_id=str(user_id) if user_id is not None else (str(user.id) if user is not None else None),
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        payload_hash=payload_sha256(payload),
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        ts=datetime.now(UTC),
    )
    db.add(event)
    return event
