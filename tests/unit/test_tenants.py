from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.endpoints.tenants import (
    create_tenant,
    get_tenant,
    invite_tenant_user,
    list_tenants,
    update_tenant,
)
from app.core.security import verify_password
from app.models import PlanTier, Tenant, TenantStatus, User, UserRole
from app.schemas.tenants import (
    TenantCreateRequest,
    TenantUpdateRequest,
    TenantUserInviteRequest,
)


def _request() -> MagicMock:
    request = MagicMock()
    request.headers = {"user-agent": "pytest"}
    client = MagicMock()
    client.host = "127.0.0.1"
    request.client = client
    return request


def _scalar_result(*, scalar_one=None, scalar_one_or_none=None):
    result = MagicMock()
    if scalar_one is not None:
        result.scalar_one.return_value = scalar_one
    if scalar_one_or_none is not None:
        result.scalar_one_or_none.return_value = scalar_one_or_none
    return result


def _scalars_result(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def make_tenant(name: str = "Tenant A") -> Tenant:
    now = datetime.now(UTC)
    return Tenant(
        id="tenant-1",
        name=name,
        slug=name.lower().replace(" ", "-"),
        plan_tier=PlanTier.pro,
        status=TenantStatus.active,
        max_vcpus=32,
        max_ram_gb=128,
        max_storage_gb=2048,
        max_backup_gb=1024,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_create_tenant_creates_first_admin_atomically() -> None:
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.execute.side_effect = [_scalar_result(scalar_one=1), _scalar_result(scalar_one=0)]

    added: list[object] = []
    db.add.side_effect = lambda obj: added.append(obj)

    response = await create_tenant(
        TenantCreateRequest(
            name="Acme MSP",
            slug="acme-msp",
            plan_tier=PlanTier.enterprise,
            max_vcpus=64,
            max_ram_gb=256,
            max_storage_gb=4096,
            max_backup_gb=2048,
            admin_email="admin@acme.example.com",
            admin_password="super-secret-123",
            admin_full_name="Acme Admin",
        ),
        _request(),
        db,
        MagicMock(),
    )

    tenant = next(obj for obj in added if isinstance(obj, Tenant))
    admin_user = next(obj for obj in added if isinstance(obj, User))

    assert tenant.slug == "acme-msp"
    assert admin_user.role == UserRole.tenant_admin
    assert verify_password("super-secret-123", admin_user.hashed_password)
    assert response.user_count == 1
    assert response.vm_count == 0
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_list_tenants_returns_paginated_response() -> None:
    db = AsyncMock()
    tenants = [make_tenant("Tenant A"), make_tenant("Tenant B")]
    tenants[1].id = "tenant-2"
    tenants[1].slug = "tenant-b"

    db.execute.side_effect = [
        _scalar_result(scalar_one=2),
        _scalars_result(tenants),
        _scalar_result(scalar_one=3),
        _scalar_result(scalar_one=7),
        _scalar_result(scalar_one=4),
        _scalar_result(scalar_one=9),
    ]

    response = await list_tenants(db, MagicMock(), page=1, page_size=25)

    assert response.total == 2
    assert len(response.items) == 2
    assert response.items[0].id == "tenant-1"
    assert response.items[1].id == "tenant-2"
    assert response.items[0].user_count == 3
    assert response.items[0].vm_count == 7
    assert response.items[1].user_count == 4
    assert response.items[1].vm_count == 9


@pytest.mark.asyncio
async def test_get_tenant_returns_counts() -> None:
    db = AsyncMock()
    tenant = make_tenant()
    db.execute.side_effect = [
        _scalar_result(scalar_one_or_none=tenant),
        _scalar_result(scalar_one=3),
        _scalar_result(scalar_one=7),
    ]

    response = await get_tenant(tenant.id, db, MagicMock())

    assert response.id == tenant.id
    assert response.user_count == 3
    assert response.vm_count == 7


@pytest.mark.asyncio
async def test_update_tenant_applies_partial_fields() -> None:
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()

    tenant = make_tenant()
    db.execute.side_effect = [
        _scalar_result(scalar_one_or_none=tenant),
        _scalar_result(scalar_one=4),
        _scalar_result(scalar_one=9),
    ]

    response = await update_tenant(
        tenant.id,
        TenantUpdateRequest(
            name="Updated Tenant",
            plan_tier=PlanTier.enterprise,
            max_vcpus=128,
        ),
        _request(),
        db,
        MagicMock(),
    )

    assert tenant.name == "Updated Tenant"
    assert tenant.plan_tier == PlanTier.enterprise
    assert tenant.max_vcpus == 128
    assert response.user_count == 4
    assert response.vm_count == 9
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_invite_tenant_user_hashes_password() -> None:
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.execute.side_effect = [_scalar_result(scalar_one_or_none="tenant-1")]

    added: list[User] = []
    db.add.side_effect = lambda obj: added.append(obj)

    response = await invite_tenant_user(
        "tenant-1",
        TenantUserInviteRequest(
            email="viewer@acme.example.com",
            password="another-secret-123",
            full_name="Read Only",
            role=UserRole.viewer,
        ),
        _request(),
        db,
        MagicMock(),
    )

    created_users = [obj for obj in added if isinstance(obj, User)]
    assert len(created_users) == 1
    assert created_users[0].tenant_id == "tenant-1"
    assert verify_password("another-secret-123", created_users[0].hashed_password)
    assert response.email == "viewer@acme.example.com"
    assert response.role == UserRole.viewer