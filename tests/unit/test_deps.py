from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import pytest

from app.core.deps import _get_tenant_db
from app.models import UserRole


@pytest.mark.asyncio
async def test_get_tenant_db_uses_msp_admin_bypass() -> None:
    captured: list[str] = []

    @asynccontextmanager
    async def fake_tenant_session(tenant_id: str):
        captured.append(tenant_id)
        yield "tenant-db"

    user = MagicMock()
    user.role = UserRole.msp_admin
    user.tenant_id = "tenant-a"

    with patch("app.core.deps.tenant_session", fake_tenant_session):
        gen = _get_tenant_db(user)
        db = await anext(gen)
        assert db == "tenant-db"
        await gen.aclose()

    assert captured == ["MSP_ADMIN_BYPASS"]


@pytest.mark.asyncio
async def test_get_tenant_db_uses_user_tenant_for_non_msp_admin() -> None:
    captured: list[str] = []

    @asynccontextmanager
    async def fake_tenant_session(tenant_id: str):
        captured.append(tenant_id)
        yield "tenant-db"

    user = MagicMock()
    user.role = UserRole.tenant_admin
    user.tenant_id = "tenant-b"

    with patch("app.core.deps.tenant_session", fake_tenant_session):
        gen = _get_tenant_db(user)
        db = await anext(gen)
        assert db == "tenant-db"
        await gen.aclose()

    assert captured == ["tenant-b"]