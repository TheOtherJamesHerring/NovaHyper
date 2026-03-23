"""
app/api/v1/endpoints/tenants.py
--------------------------------
Tenant management endpoints. All operations are MSP-admin only.
"""
import hashlib
import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.core.deps import CurrentUser, MSPAdminOnly, TenantDBForMSP
from app.core.security import hash_password
from app.models import AuditLog, Tenant, TenantStatus, User, UserRole, VM, VMStatus
from app.schemas import PaginatedResponse
from app.schemas.tenants import (
    TenantCreateRequest,
    TenantDetailResponse,
    TenantResponse,
    TenantReinstateRequest,
    TenantSuspendRequest,
    TenantUpdateRequest,
    TenantUserInviteRequest,
    TenantUserResponse,
)
from app.services.vm_service import VMService

router = APIRouter(prefix="/tenants", tags=["tenants"], dependencies=[MSPAdminOnly])


async def _write_audit_event(
    db,
    actor: User,
    action: str,
    target_tenant_id: str | None,
    resource_type: str,
    resource_id: str | None,
    reason: str | None = None,
) -> None:
    actor_id = str(actor.id)
    payload = {
        "actor_user_id": actor_id,
        "action": action,
        "target_tenant_id": target_tenant_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "reason": reason,
        "ts": datetime.now(UTC).isoformat(),
    }
    payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            tenant_id=target_tenant_id,
            user_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            payload_hash=payload_hash,
            reason=reason,
            ts=datetime.now(UTC),
        )
    )


async def _tenant_counts(db, tenant_id: str) -> tuple[int, int]:
    user_count = (
        await db.execute(select(func.count(User.id)).where(User.tenant_id == tenant_id))
    ).scalar_one()
    vm_count = (
        await db.execute(
            select(func.count(VM.id)).where(VM.tenant_id == tenant_id, VM.status != VMStatus.deleted)
        )
    ).scalar_one()
    return user_count, vm_count


async def _tenant_detail_response(db, tenant: Tenant) -> TenantDetailResponse:
    user_count, vm_count = await _tenant_counts(db, tenant.id)
    response = TenantResponse.model_validate(tenant, from_attributes=True)
    return TenantDetailResponse(**response.model_dump(), user_count=user_count, vm_count=vm_count)


@router.post(
    "",
    response_model=TenantDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tenant and first tenant admin",
)
async def create_tenant(body: TenantCreateRequest, db: TenantDBForMSP, user: CurrentUser) -> TenantDetailResponse:
    now = datetime.now(UTC)
    tenant = Tenant(
        id=str(uuid.uuid4()),
        name=body.name,
        slug=body.slug,
        plan_tier=body.plan_tier,
        status=TenantStatus.active,
        max_vcpus=body.max_vcpus,
        max_ram_gb=body.max_ram_gb,
        max_storage_gb=body.max_storage_gb,
        max_backup_gb=body.max_backup_gb,
        created_at=now,
        updated_at=now,
    )
    admin_user = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        email=str(body.admin_email).lower(),
        hashed_password=hash_password(body.admin_password),
        full_name=body.admin_full_name,
        role=UserRole.tenant_admin,
        is_active=True,
        created_at=now,
    )

    db.add(tenant)
    db.add(admin_user)

    try:
        await db.flush()
        await _write_audit_event(
            db,
            actor=user,
            action="tenant.create",
            target_tenant_id=tenant.id,
            resource_type="tenant",
            resource_id=tenant.id,
        )
        response = TenantDetailResponse(
            **TenantResponse.model_validate(tenant, from_attributes=True).model_dump(),
            user_count=1,
            vm_count=0,
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant or user already exists")

    return response


@router.get("", response_model=PaginatedResponse[TenantDetailResponse], summary="List all tenants")
async def list_tenants(
    db: TenantDBForMSP,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> PaginatedResponse[TenantDetailResponse]:
    q = select(Tenant)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    tenants = (
        await db.execute(
            q.order_by(Tenant.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()

    items: list[TenantDetailResponse] = []
    for tenant in tenants:
        items.append(await _tenant_detail_response(db, tenant))

    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, has_more=(page * page_size) < total)


@router.get("/{tenant_id}", response_model=TenantDetailResponse, summary="Get tenant detail")
async def get_tenant(tenant_id: str, db: TenantDBForMSP, user: CurrentUser) -> TenantDetailResponse:
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return await _tenant_detail_response(db, tenant)


@router.patch("/{tenant_id}", response_model=TenantDetailResponse, summary="Update a tenant")
async def update_tenant(
    tenant_id: str,
    body: TenantUpdateRequest,
    db: TenantDBForMSP,
    user: CurrentUser,
) -> TenantDetailResponse:
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(tenant, field, value)

    await _write_audit_event(
        db,
        actor=user,
        action="tenant.update",
        target_tenant_id=tenant.id,
        resource_type="tenant",
        resource_id=tenant.id,
    )
    response = await _tenant_detail_response(db, tenant)
    await db.commit()
    return response


@router.post(
    "/{tenant_id}/users",
    response_model=TenantUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user in a tenant",
)
async def invite_tenant_user(
    tenant_id: str,
    body: TenantUserInviteRequest,
    db: TenantDBForMSP,
    user: CurrentUser,
) -> TenantUserResponse:
    tenant = (await db.execute(select(Tenant.id).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    new_user = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        email=str(body.email).lower(),
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        is_active=body.is_active,
        created_at=datetime.now(UTC),
    )
    db.add(new_user)

    try:
        await db.flush()
        await _write_audit_event(
            db,
            actor=user,
            action="tenant.user_invite",
            target_tenant_id=tenant_id,
            resource_type="user",
            resource_id=new_user.id,
        )
        response = TenantUserResponse.model_validate(new_user, from_attributes=True)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    return response


@router.post("/{tenant_id}/suspend", response_model=TenantDetailResponse, summary="Suspend tenant and stop VMs")
async def suspend_tenant(
    tenant_id: str,
    body: TenantSuspendRequest,
    db: TenantDBForMSP,
    user: CurrentUser,
) -> TenantDetailResponse:
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    vm_service = VMService(db)
    vms = (
        await db.execute(
            select(VM).where(
                VM.tenant_id == tenant_id,
                VM.status.in_([VMStatus.running, VMStatus.paused, VMStatus.provisioning]),
            )
        )
    ).scalars().all()
    for vm in vms:
        if vm.status in (VMStatus.running, VMStatus.paused):
            await vm_service.perform_action(vm, "stop", force=True)
        else:
            vm.status = VMStatus.stopped

    tenant.status = TenantStatus.suspended
    await _write_audit_event(
        db,
        actor=user,
        action="tenant.suspend",
        target_tenant_id=tenant.id,
        resource_type="tenant",
        resource_id=tenant.id,
        reason=body.reason,
    )
    response = await _tenant_detail_response(db, tenant)
    await db.commit()
    return response


@router.post("/{tenant_id}/reinstate", response_model=TenantDetailResponse, summary="Reinstate suspended tenant")
async def reinstate_tenant(
    tenant_id: str,
    body: TenantReinstateRequest,
    db: TenantDBForMSP,
    user: CurrentUser,
) -> TenantDetailResponse:
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    tenant.status = TenantStatus.active
    await _write_audit_event(
        db,
        actor=user,
        action="tenant.reinstate",
        target_tenant_id=tenant.id,
        resource_type="tenant",
        resource_id=tenant.id,
        reason=body.reason,
    )
    response = await _tenant_detail_response(db, tenant)
    await db.commit()
    return response


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete suspended tenant")
async def delete_tenant(tenant_id: str, db: TenantDBForMSP, user: CurrentUser) -> None:
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    if tenant.status != TenantStatus.suspended:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant must be suspended before deletion")

    vm_count = (
        await db.execute(select(func.count(VM.id)).where(VM.tenant_id == tenant_id, VM.status != VMStatus.deleted))
    ).scalar_one()
    if vm_count != 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant still has active VMs")

    await _write_audit_event(
        db,
        actor=user,
        action="tenant.delete",
        target_tenant_id=tenant.id,
        resource_type="tenant",
        resource_id=tenant.id,
    )
    await db.execute(delete(Tenant).where(Tenant.id == tenant.id))
    await db.commit()