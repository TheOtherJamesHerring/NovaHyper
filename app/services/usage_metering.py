"""Deprecated compatibility layer for legacy usage metering imports.

The active implementation lives in app/services/metering.py.
"""

from __future__ import annotations

import warnings
from datetime import datetime
from typing import Any

from app.services.metering import MeteringService, emit_usage_events_batch


def _warn_deprecated() -> None:
    warnings.warn(
        "app.services.usage_metering is deprecated; use app.services.metering instead.",
        DeprecationWarning,
        stacklevel=2,
    )


async def record_usage_snapshot(db: Any, recorded_at: datetime | None = None) -> int:
    _warn_deprecated()
    return await emit_usage_events_batch(db, recorded_at=recorded_at)


class UsageMeteringService(MeteringService):
    def __init__(self, interval_seconds: int = 60, session_factory: Any = None) -> None:
        _warn_deprecated()
        if session_factory is None:
            super().__init__(interval_seconds=interval_seconds)
            return
        super().__init__(interval_seconds=interval_seconds, session_factory=session_factory)