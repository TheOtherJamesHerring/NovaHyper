"""app/services/metering.py — Batched usage metering for running VMs."""
import asyncio
import contextlib
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import insert, select

from app.db.session import AsyncSessionLocal
from app.models import UsageEvent, VM, VMStatus

log = structlog.get_logger(__name__)


async def emit_usage_events_batch(db: Any, recorded_at: datetime | None = None) -> int:
    result = await db.execute(
        select(VM.id, VM.tenant_id, VM.vcpus, VM.ram_mb).where(VM.status == VMStatus.running)
    )
    running_vms = result.all()
    if not running_vms:
        return 0

    ts = recorded_at or datetime.now(UTC)
    rows: list[dict[str, Any]] = []
    for vm_id, tenant_id, vcpus, ram_mb in running_vms:
        rows.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "resource_type": "vm_vcpu",
                "resource_id": vm_id,
                "quantity": float(vcpus),
                "unit": "vcpu-minutes",
                "recorded_at": ts,
            }
        )
        rows.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "resource_type": "vm_ram",
                "resource_id": vm_id,
                "quantity": float(ram_mb) / 1024,
                "unit": "gb-minutes",
                "recorded_at": ts,
            }
        )

    await db.execute(insert(UsageEvent), rows)
    await db.commit()
    return len(rows)


class MeteringService:
    def __init__(self, interval_seconds: int = 60, session_factory: Any = AsyncSessionLocal) -> None:
        self._interval_seconds = interval_seconds
        self._session_factory = session_factory
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def run_once(self) -> int:
        async with self._session_factory() as session:
            emitted = await emit_usage_events_batch(session)
            log.info("metering.snapshot", emitted=emitted)
            return emitted

    async def run_forever(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self.run_once()
            except Exception as exc:
                log.error("metering.failed", error=str(exc))

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._interval_seconds)
            except TimeoutError:
                continue

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self.run_forever())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
