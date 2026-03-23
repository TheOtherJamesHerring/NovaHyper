from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.audit import (
    export_audit_events_csv,
    list_audit_events,
    verify_audit_event,
)
from app.models import AuditLog, UserRole
from app.services.audit import payload_sha256


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one.return_value = value
    return result


def _scalars_result(values):
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    return result


def _sample_event(event_id: str, tenant_id: str, action: str, ts: datetime) -> AuditLog:
    payload = {
        "tenant_id": tenant_id,
        "user_id": "user-1",
        "action": action,
        "resource_type": "vm",
        "resource_id": "vm-1",
    }
    return AuditLog(
        id=event_id,
        tenant_id=tenant_id,
        user_id="user-1",
        action=action,
        resource_type="vm",
        resource_id="vm-1",
        payload_hash=payload_sha256(payload),
        ip_address="127.0.0.1",
        user_agent="pytest",
        ts=ts,
    )


@pytest.mark.asyncio
async def test_list_audit_filters_by_action() -> None:
    db = AsyncMock()
    event = _sample_event("a-1", "tenant-1", "vm.create", datetime.now(UTC))
    db.execute.side_effect = [_scalar_result(1), _scalars_result([event])]

    response = await list_audit_events(db, MagicMock(), page=1, page_size=25, action="vm.create")

    assert response.total == 1
    assert len(response.items) == 1
    assert response.items[0].action == "vm.create"


@pytest.mark.asyncio
async def test_list_audit_filters_by_date_range() -> None:
    db = AsyncMock()
    now = datetime.now(UTC)
    db.execute.side_effect = [_scalar_result(0), _scalars_result([])]

    await list_audit_events(
        db,
        MagicMock(),
        page=1,
        page_size=25,
        from_ts=now - timedelta(days=1),
        to_ts=now,
    )

    first_query = db.execute.await_args_list[0].args[0]
    compiled = str(first_query)
    assert "audit_log.ts >=" in compiled
    assert "audit_log.ts <=" in compiled


@pytest.mark.asyncio
async def test_audit_tenant_isolation() -> None:
    db = AsyncMock()
    event = _sample_event("b-1", "tenant-b", "vm.create", datetime.now(UTC))
    db.execute.side_effect = [_scalar_result(1), _scalars_result([event])]

    tenant_b_user = MagicMock()
    tenant_b_user.tenant_id = "tenant-b"

    response = await list_audit_events(db, tenant_b_user, page=1, page_size=25)

    assert len(response.items) == 1
    assert all(item.tenant_id == "tenant-b" for item in response.items)


@pytest.mark.asyncio
async def test_csv_export_requires_msp_admin() -> None:
    db = AsyncMock()
    operator = MagicMock()
    operator.role = UserRole.operator

    with pytest.raises(HTTPException) as exc:
        await export_audit_events_csv(
            db=db,
            user=operator,
            tenant_id="tenant-1",
            from_ts=datetime.now(UTC) - timedelta(days=1),
            to_ts=datetime.now(UTC),
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_verify_returns_true_for_unmodified_record() -> None:
    event = _sample_event("v-1", "tenant-1", "vm.create", datetime.now(UTC))
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = event
    db.execute.return_value = result

    response = await verify_audit_event("v-1", db, MagicMock())

    assert response.verified is True
    assert response.id == "v-1"
