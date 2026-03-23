import os
import uuid

import httpx
import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models import AuditLog, Tenant, User, VM, VMStatus


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
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_tenant_lifecycle_create_suspend_reinstate_delete() -> None:
    suffix = uuid.uuid4().hex[:8]
    tenant_id: str | None = None
    user_id: str | None = None

    async with httpx.AsyncClient(base_url=_base_url(), timeout=30.0) as client:
        msp_email, msp_password = _msp_admin_credentials()
        msp_token = await _login(client, msp_email, msp_password)
        msp_headers = {"Authorization": f"Bearer {msp_token}"}

        create_response = await client.post(
            "/api/v1/tenants",
            headers=msp_headers,
            json={
                "name": f"Lifecycle Tenant {suffix}",
                "slug": f"lifecycle-tenant-{suffix}",
                "plan_tier": "starter",
                "admin_email": f"lifecycle-{suffix}@example.com",
                "admin_password": "lifecycle-secret-123",
                "admin_full_name": "Lifecycle Admin",
            },
        )
        assert create_response.status_code == 201, create_response.text
        tenant_payload = create_response.json()
        tenant_id = tenant_payload["id"]

        tenant_token = await _login(client, f"lifecycle-{suffix}@example.com", "lifecycle-secret-123")
        tenant_headers = {"Authorization": f"Bearer {tenant_token}"}

        suspend_response = await client.post(
            f"/api/v1/tenants/{tenant_id}/suspend",
            headers=msp_headers,
            json={"reason": "invoice_overdue"},
        )
        assert suspend_response.status_code == 200, suspend_response.text

        blocked_after_suspend = await client.get("/api/v1/vms", headers=tenant_headers)
        assert blocked_after_suspend.status_code == 403, blocked_after_suspend.text

        reinstate_response = await client.post(
            f"/api/v1/tenants/{tenant_id}/reinstate",
            headers=msp_headers,
            json={"reason": "payment_received"},
        )
        assert reinstate_response.status_code == 200, reinstate_response.text

        allowed_after_reinstate = await client.get("/api/v1/vms", headers=tenant_headers)
        assert allowed_after_reinstate.status_code == 200, allowed_after_reinstate.text

        suspend_again = await client.post(
            f"/api/v1/tenants/{tenant_id}/suspend",
            headers=msp_headers,
            json={"reason": "close_account"},
        )
        assert suspend_again.status_code == 200, suspend_again.text

        delete_response = await client.delete(f"/api/v1/tenants/{tenant_id}", headers=msp_headers)
        assert delete_response.status_code == 204, delete_response.text

    async with TestSessionLocal() as db:
        tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
        assert tenant is None

        user = (await db.execute(select(User).where(User.email == f"lifecycle-{suffix}@example.com"))).scalar_one_or_none()
        assert user is None

        actions = (
            await db.execute(
                select(AuditLog.action, AuditLog.reason).where(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.action.in_(["tenant.suspend", "tenant.reinstate", "tenant.delete"]),
                )
            )
        ).all()
        action_names = [row[0] for row in actions]
        assert "tenant.suspend" in action_names
        assert "tenant.reinstate" in action_names
        assert "tenant.delete" in action_names