from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.requests import Request

from app.models import AuditLog
from app.services.audit import payload_sha256, write_audit_event


TEST_DATABASE_URL = os.getenv(
    "NOVAHYPER_TEST_DATABASE_URL",
    "postgresql+asyncpg://novahyper:novahyper@localhost:5432/novahyper",
)
test_engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)


def _request() -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/test",
        "headers": [(b"user-agent", b"pytest")],
        "client": ("127.0.0.1", 5000),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_payload_hash_is_sha256() -> None:
    payload = {"resource_id": "vm-1", "action": "vm.create"}
    digest = payload_sha256(payload)
    assert len(digest) == 64
    assert digest == payload_sha256({"action": "vm.create", "resource_id": "vm-1"})


@pytest.mark.asyncio
async def test_audit_event_written_in_same_transaction() -> None:
    user = MagicMock()
    user.id = str(uuid.uuid4())
    user.tenant_id = str(uuid.uuid4())

    event_id: str | None = None
    async with TestSessionLocal() as db:
        try:
            async with db.begin():
                event = await write_audit_event(
                    db=db,
                    request=_request(),
                    user=user,
                    action="vm.create",
                    resource_type="vm",
                    resource_id="vm-tx-test",
                    payload={
                        "tenant_id": user.tenant_id,
                        "user_id": user.id,
                        "action": "vm.create",
                        "resource_type": "vm",
                        "resource_id": "vm-tx-test",
                    },
                )
                event_id = event.id
                raise RuntimeError("force rollback")
        except RuntimeError:
            pass

        row = (await db.execute(select(AuditLog).where(AuditLog.id == event_id))).scalar_one_or_none()
        assert row is None


@pytest.mark.asyncio
async def test_audit_log_rejects_update() -> None:
    event_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    async with TestSessionLocal() as db:
        db.add(
            AuditLog(
                id=event_id,
                tenant_id=tenant_id,
                user_id=user_id,
                action="vm.create",
                resource_type="vm",
                resource_id="vm-upd",
                payload_hash=payload_sha256(
                    {
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "action": "vm.create",
                        "resource_type": "vm",
                        "resource_id": "vm-upd",
                    }
                ),
                ip_address="127.0.0.1",
                user_agent="pytest",
                ts=datetime.now(UTC),
            )
        )
        await db.commit()

        with pytest.raises(Exception):
            await db.execute(text("UPDATE audit_log SET action = 'vm.delete' WHERE id = :id"), {"id": event_id})

        await db.rollback()


@pytest.mark.asyncio
async def test_audit_log_rejects_delete() -> None:
    event_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    async with TestSessionLocal() as db:
        db.add(
            AuditLog(
                id=event_id,
                tenant_id=tenant_id,
                user_id=user_id,
                action="vm.create",
                resource_type="vm",
                resource_id="vm-del",
                payload_hash=payload_sha256(
                    {
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "action": "vm.create",
                        "resource_type": "vm",
                        "resource_id": "vm-del",
                    }
                ),
                ip_address="127.0.0.1",
                user_agent="pytest",
                ts=datetime.now(UTC),
            )
        )
        await db.commit()

        with pytest.raises(Exception):
            await db.execute(delete(AuditLog).where(AuditLog.id == event_id))

        await db.rollback()
