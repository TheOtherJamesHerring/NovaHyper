from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.usage_metering import UsageMeteringService, record_usage_snapshot


def _rows_result(items):
    result = MagicMock()
    result.all.return_value = items
    return result


@pytest.mark.asyncio
async def test_record_usage_snapshot_emits_two_events_per_running_vm() -> None:
    db = AsyncMock()
    db.commit = AsyncMock()
    db.execute.side_effect = [
        _rows_result([("vm-1", "tenant-1", 4, 8192)]),
        MagicMock(),
    ]

    emitted = await record_usage_snapshot(db, recorded_at=datetime(2026, 3, 23, tzinfo=UTC))

    assert emitted == 2
    assert db.execute.await_count == 2
    inserted_rows = db.execute.await_args_list[1].args[1]
    assert inserted_rows[0]["resource_type"] == "vm_vcpu"
    assert inserted_rows[0]["quantity"] == 4.0
    assert inserted_rows[0]["unit"] == "vcpu-minutes"
    assert inserted_rows[1]["resource_type"] == "vm_ram"
    assert inserted_rows[1]["quantity"] == 8.0
    assert inserted_rows[1]["unit"] == "gb-minutes"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_record_usage_snapshot_skips_commit_when_no_running_vms() -> None:
    db = AsyncMock()
    db.commit = AsyncMock()
    db.execute.return_value = _rows_result([])

    emitted = await record_usage_snapshot(db)

    assert emitted == 0
    assert db.execute.await_count == 1
    db.commit.assert_not_called()


class _SessionContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return None


@pytest.mark.asyncio
async def test_usage_metering_service_run_once_uses_session_factory() -> None:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.execute.side_effect = [
        _rows_result([("vm-1", "tenant-1", 4, 8192)]),
        MagicMock(),
    ]

    service = UsageMeteringService(
        interval_seconds=1,
        session_factory=lambda: _SessionContext(session),
    )

    emitted = await service.run_once()

    assert emitted == 2
    session.commit.assert_called_once()