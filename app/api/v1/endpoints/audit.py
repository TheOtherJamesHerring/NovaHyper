"""Audit log API endpoints.

Verification checks whether the stored integrity hash still matches the hash
recomputed from immutable row fields. Because raw operation payloads are never
stored, this proves database-level tamper detection for the stored record but
cannot reconstruct the original payload body.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, desc, func, select

from app.core.deps import CurrentUser, MSPAdminOnly, OperatorUp, TenantDB, TenantDBForMSP
from app.models import AuditLog, UserRole
from app.schemas import PaginatedResponse
from app.schemas.audit import AuditEventResponse, AuditVerifyResponse
from app.services.audit import payload_sha256

router = APIRouter(prefix="/audit", tags=["audit"], dependencies=[OperatorUp])


def _to_response(event: AuditLog) -> AuditEventResponse:
    return AuditEventResponse(
        id=event.id,
        tenant_id=event.tenant_id,
        user_id=event.user_id,
        action=event.action,
        resource_type=event.resource_type,
        resource_id=event.resource_id,
        integrity_hash=event.payload_hash,
        ip_address=event.ip_address,
        user_agent=event.user_agent,
        ts=event.ts,
    )


def _verification_payload(event: AuditLog) -> dict[str, str | None]:
    return {
        "tenant_id": event.tenant_id,
        "user_id": event.user_id,
        "action": event.action,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
    }


@router.get("", response_model=PaginatedResponse[AuditEventResponse], summary="List tenant audit events")
async def list_audit_events(
    db: TenantDB,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    action: str | None = Query(None),
    user_id: str | None = Query(None),
    resource_type: str | None = Query(None),
    resource_id: str | None = Query(None),
    from_ts: datetime | None = Query(None),
    to_ts: datetime | None = Query(None),
) -> PaginatedResponse[AuditEventResponse]:
    q = select(AuditLog)
    if action:
        q = q.where(AuditLog.action == action)
    if user_id:
        q = q.where(AuditLog.user_id == user_id)
    if resource_type:
        q = q.where(AuditLog.resource_type == resource_type)
    if resource_id:
        q = q.where(AuditLog.resource_id == resource_id)
    if from_ts:
        q = q.where(AuditLog.ts >= from_ts)
    if to_ts:
        q = q.where(AuditLog.ts <= to_ts)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    result = await db.execute(
        q.order_by(desc(AuditLog.ts)).offset((page - 1) * page_size).limit(page_size)
    )
    events = result.scalars().all()

    return PaginatedResponse(
        items=[_to_response(event) for event in events],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/export", dependencies=[MSPAdminOnly], summary="Export tenant audit events as CSV")
async def export_audit_events_csv(
    db: TenantDBForMSP,
    user: CurrentUser,
    tenant_id: str = Query(...),
    from_ts: datetime = Query(...),
    to_ts: datetime = Query(...),
) -> StreamingResponse:
    if user.role != UserRole.msp_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    if to_ts < from_ts:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="to_ts must be >= from_ts")

    stmt = (
        select(AuditLog)
        .where(
            and_(
                AuditLog.tenant_id == tenant_id,
                AuditLog.ts >= from_ts,
                AuditLog.ts <= to_ts,
            )
        )
        .order_by(AuditLog.ts.desc())
    )

    async def _stream_csv():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            "id",
            "tenant_id",
            "user_id",
            "action",
            "resource_type",
            "resource_id",
            "integrity_hash",
            "ip_address",
            "user_agent",
            "ts",
        ])
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)

        stream = await db.stream(stmt)
        async for event in stream.scalars():
            writer.writerow([
                event.id,
                event.tenant_id or "",
                event.user_id or "",
                event.action,
                event.resource_type,
                event.resource_id or "",
                event.payload_hash,
                event.ip_address or "",
                event.user_agent or "",
                event.ts.isoformat(),
            ])
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    stamp = datetime.now(UTC).strftime("%Y%m%d")
    filename = f"audit_{tenant_id}_{stamp}.csv"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(_stream_csv(), media_type="text/csv", headers=headers)


@router.get("/{audit_id}", response_model=AuditEventResponse, summary="Get one audit event")
async def get_audit_event(audit_id: str, db: TenantDB, user: CurrentUser) -> AuditEventResponse:
    event = (await db.execute(select(AuditLog).where(AuditLog.id == audit_id))).scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit event not found")
    return _to_response(event)


@router.get("/{audit_id}/verify", response_model=AuditVerifyResponse, summary="Verify one audit event integrity")
async def verify_audit_event(audit_id: str, db: TenantDB, user: CurrentUser) -> AuditVerifyResponse:
    """Verify audit row integrity against immutable row fields.

    This endpoint verifies database-level tamper detection for the persisted
    audit row. It does not recover the original operation payload because the
    raw payload is intentionally not stored in the database.
    """
    event = (await db.execute(select(AuditLog).where(AuditLog.id == audit_id))).scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit event not found")

    recomputed = payload_sha256(_verification_payload(event))
    if recomputed == event.payload_hash:
        return AuditVerifyResponse(verified=True, id=event.id)
    return AuditVerifyResponse(verified=False, id=event.id, reason="hash_mismatch")
