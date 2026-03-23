"""app/services/partition_manager.py — Periodic usage partition provisioning."""
import asyncio
import contextlib
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.sql import text

from app.db.session import AsyncSessionLocal

log = structlog.get_logger(__name__)


def _month_offset(dt: datetime, offset: int) -> tuple[int, int]:
    total_months = (dt.year * 12) + (dt.month - 1) + offset
    year = total_months // 12
    month = (total_months % 12) + 1
    return year, month


async def ensure_partitions_exist(db: Any, now: datetime | None = None) -> list[tuple[int, int]]:
    base = now or datetime.now(UTC)
    months = [_month_offset(base, idx) for idx in range(3)]

    for year, month in months:
        await db.execute(
            text("SELECT create_monthly_partition(:year, :month)"),
            {"year": year, "month": month},
        )

    return months


class PartitionManagerService:
    def __init__(self, interval_seconds: int = 86400, session_factory: Any = AsyncSessionLocal) -> None:
        self._interval_seconds = interval_seconds
        self._session_factory = session_factory
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def run_once(self) -> list[tuple[int, int]]:
        async with self._session_factory() as session:
            months = await ensure_partitions_exist(session)
            await session.commit()
            log.info("partition_manager.ensure", months=months)
            return months

    async def run_forever(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self.run_once()
            except Exception as exc:
                log.error("partition_manager.failed", error=str(exc))

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._interval_seconds)
            except TimeoutError:
                continue

    async def start(self) -> None:
        try:
            await self.run_once()
        except Exception as exc:
            log.error("partition_manager.start_failed", error=str(exc))
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self.run_forever())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None