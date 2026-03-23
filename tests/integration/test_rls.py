import os
import uuid

import httpx
import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models import Tenant, VM, VMStatus


TEST_DATABASE_URL = os.getenv(
    "NOVAHYPER_TEST_DATABASE_URL",
    "postgresql+asyncpg://novahyper:novahyper@localhost:5432/novahyper",
)
test_engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)


def _base_url() -> str:
    return os.getenv("NOVAHYPER_API_BASE_URL", "http://localhost:8000")


def _msp_admin_credentials() -> tuple[str, str]:
    settings = get_settings()
    email = settings.BOOTSTRAP_ADMIN_EMAIL or "jherring@m-theorygrp.com"
    password = settings.BOOTSTRAP_ADMIN_PASSWORD or "changeme123!"
    return email, password


async def _login(client: httpx.AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def _cleanup(tenant_ids: list[str], vm_id: str | None) -> None:
    async with TestSessionLocal() as db:
        if vm_id:
            await db.execute(delete(VM).where(VM.id == vm_id))
        if tenant_ids:
            await db.execute(delete(Tenant).where(Tenant.id.in_(tenant_ids)))
        await db.commit()


@pytest.mark.asyncio
async def test_rls_smoke_for_tenant_and_msp_admin_access() -> None:
    suffix = uuid.uuid4().hex[:8]
    tenant_ids: list[str] = []
    vm_id: str | None = None

    async with httpx.AsyncClient(base_url=_base_url(), timeout=30.0) as client:
        admin_email, admin_password = _msp_admin_credentials()
        msp_token = await _login(client, admin_email, admin_password)
        admin_headers = {"Authorization": f"Bearer {msp_token}"}

        tenant_a_response = await client.post(
            "/api/v1/tenants",
            headers=admin_headers,
            json={
                "name": f"RLS Tenant A {suffix}",
                "slug": f"rls-tenant-a-{suffix}",
                "plan_tier": "starter",
                "admin_email": f"tenant-a-{suffix}@example.com",
                "admin_password": "tenant-a-secret-123",
                "admin_full_name": "Tenant A Admin",
            },
        )
        assert tenant_a_response.status_code == 201, tenant_a_response.text
        tenant_a = tenant_a_response.json()
        tenant_ids.append(tenant_a["id"])

        tenant_b_response = await client.post(
            "/api/v1/tenants",
            headers=admin_headers,
            json={
                "name": f"RLS Tenant B {suffix}",
                "slug": f"rls-tenant-b-{suffix}",
                "plan_tier": "starter",
                "admin_email": f"tenant-b-{suffix}@example.com",
                "admin_password": "tenant-b-secret-123",
                "admin_full_name": "Tenant B Admin",
            },
        )
        assert tenant_b_response.status_code == 201, tenant_b_response.text
        tenant_b = tenant_b_response.json()
        tenant_ids.append(tenant_b["id"])

        try:
            async with TestSessionLocal() as db:
                vm = VM(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_a["id"],
                    name=f"rls-vm-{suffix}",
                    description="RLS smoke test VM",
                    status=VMStatus.running,
                    vcpus=2,
                    ram_mb=2048,
                    os_type="linux",
                    os_variant="ubuntu22.04",
                    host_id=None,
                    libvirt_uuid=None,
                    libvirt_xml=None,
                    config={},
                    backup_policy={},
                )
                db.add(vm)
                await db.commit()
                vm_id = vm.id

            tenant_b_token = await _login(
                client,
                f"tenant-b-{suffix}@example.com",
                "tenant-b-secret-123",
            )
            tenant_b_headers = {"Authorization": f"Bearer {tenant_b_token}"}

            tenant_b_vms = await client.get("/api/v1/vms", headers=tenant_b_headers)
            assert tenant_b_vms.status_code == 200, tenant_b_vms.text
            tenant_b_payload = tenant_b_vms.json()
            assert tenant_b_payload["items"] == []
            assert tenant_b_payload["total"] == 0

            msp_vms = await client.get("/api/v1/vms", headers=admin_headers)
            assert msp_vms.status_code == 200, msp_vms.text
            msp_payload = msp_vms.json()
            assert any(item["id"] == vm_id for item in msp_payload["items"])
        finally:
            await _cleanup(tenant_ids, vm_id)