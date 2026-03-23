from datetime import UTC, datetime
from unittest.mock import AsyncMock, call

import pytest

from app.services.partition_manager import _month_offset, ensure_partitions_exist


def test_month_offset_wraps_year_boundary() -> None:
    base = datetime(2026, 12, 15, tzinfo=UTC)
    assert _month_offset(base, 0) == (2026, 12)
    assert _month_offset(base, 1) == (2027, 1)
    assert _month_offset(base, 2) == (2027, 2)


@pytest.mark.asyncio
async def test_ensure_partitions_exist_calls_current_and_next_two_months() -> None:
    db = AsyncMock()
    db.execute = AsyncMock()

    months = await ensure_partitions_exist(db, now=datetime(2026, 5, 2, tzinfo=UTC))

    assert months == [(2026, 5), (2026, 6), (2026, 7)]
    assert db.execute.await_count == 3


@pytest.mark.asyncio
async def test_ensure_partitions_exist_is_idempotent() -> None:
    db = AsyncMock()
    db.execute = AsyncMock()

    first = await ensure_partitions_exist(db, now=datetime(2026, 5, 2, tzinfo=UTC))
    second = await ensure_partitions_exist(db, now=datetime(2026, 5, 2, tzinfo=UTC))

    assert first == second == [(2026, 5), (2026, 6), (2026, 7)]
    assert db.execute.await_count == 6
