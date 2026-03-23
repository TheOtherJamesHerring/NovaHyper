from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.metering import emit_usage_events_batch


def _vm_rows(rows):
    result = MagicMock()
    result.all.return_value = rows
    return result


@pytest.mark.asyncio
async def test_emit_usage_events_batch_calculates_quantities() -> None:
    db = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    db.execute.side_effect = [_vm_rows([("vm-1", "tenant-1", 4, 8192)]), MagicMock()]

    emitted = await emit_usage_events_batch(db, recorded_at=datetime(2026, 5, 1, tzinfo=UTC))

    assert emitted == 2
    assert db.execute.await_count == 2
    insert_call = db.execute.await_args_list[1]
    inserted_rows = insert_call.args[1]
    assert inserted_rows[0]["resource_type"] == "vm_vcpu"
    assert inserted_rows[0]["quantity"] == 4.0
    assert inserted_rows[0]["unit"] == "vcpu-minutes"
    assert inserted_rows[1]["resource_type"] == "vm_ram"
    assert inserted_rows[1]["quantity"] == 8.0
    assert inserted_rows[1]["unit"] == "gb-minutes"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_emit_usage_events_batch_single_insert_for_all_vms() -> None:
    db = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    db.execute.side_effect = [
        _vm_rows(
            [
                ("vm-1", "tenant-1", 2, 4096),
                ("vm-2", "tenant-1", 1, 2048),
            ]
        ),
        MagicMock(),
    ]

    emitted = await emit_usage_events_batch(db)

    assert emitted == 4
    assert db.execute.await_count == 2
    inserted_rows = db.execute.await_args_list[1].args[1]
    assert len(inserted_rows) == 4
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_emit_usage_events_batch_no_running_vms_no_insert() -> None:
    db = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(return_value=_vm_rows([]))

    emitted = await emit_usage_events_batch(db)

    assert emitted == 0
    assert db.execute.await_count == 1
    db.commit.assert_not_called()
