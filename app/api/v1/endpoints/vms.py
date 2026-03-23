"""
app/api/v1/endpoints/vms.py
---------------------------
VM lifecycle endpoints.  All operations are tenant-scoped via RLS.

libvirt integration is intentionally wrapped in ``VMService`` so tests
can swap in a mock without touching endpoint logic.
"""
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.deps import CurrentUser, OperatorUp, TenantDB, TenantAdminUp
from app.models import VM, VMStatus
from app.schemas import (
    PaginatedResponse,
    VMActionRequest,
    VMCreate,
    VMResponse,
    VMUpdate,
)
from app.services.vm_service import VMService

router = APIRouter(prefix="/vms", tags=["vms"])


# ── List ───────────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse[VMResponse], summary="List all VMs for this tenant")
async def list_vms(
    db: TenantDB,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status_filter: VMStatus | None = Query(None, alias="status"),
    search: str | None = Query(None, max_length=128),
) -> PaginatedResponse[VMResponse]:
    q = select(VM).where(VM.status != VMStatus.deleted)

    if status_filter:
        q = q.where(VM.status == status_filter)
    if search:
        q = q.where(VM.name.ilike(f"%{search}%"))

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()

    q = q.order_by(VM.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    vms = result.scalars().all()

    return PaginatedResponse(
        items=[VMResponse.model_validate(v, from_attributes=True) for v in vms],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


# ── Get ────────────────────────────────────────────────────────────────────────

@router.get("/{vm_id}", response_model=VMResponse, summary="Get VM details")
async def get_vm(vm_id: str, db: TenantDB, user: CurrentUser) -> VMResponse:
    result = await db.execute(select(VM).where(VM.id == vm_id, VM.status != VMStatus.deleted))
    vm = result.scalar_one_or_none()
    if vm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VM not found")
    return VMResponse.model_validate(vm, from_attributes=True)


# ── Create ─────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=VMResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[OperatorUp],
    summary="Provision a new VM",
)
async def create_vm(body: VMCreate, db: TenantDB, user: CurrentUser) -> VMResponse:
    service = VMService(db)
    vm = await service.create(user.tenant_id, body)
    return VMResponse.model_validate(vm, from_attributes=True)


# ── Update ─────────────────────────────────────────────────────────────────────

@router.patch(
    "/{vm_id}",
    response_model=VMResponse,
    dependencies=[OperatorUp],
    summary="Update VM metadata / resource allocation",
)
async def update_vm(vm_id: str, body: VMUpdate, db: TenantDB, user: CurrentUser) -> VMResponse:
    result = await db.execute(select(VM).where(VM.id == vm_id))
    vm = result.scalar_one_or_none()
    if vm is None:
        raise HTTPException(status_code=404, detail="VM not found")

    update_data = body.model_dump(exclude_none=True)
    for field, value in update_data.items():
        if field == "tags":
            vm.config = {**(vm.config or {}), "tags": value}
            continue
        setattr(vm, field, value)
    await db.commit()
    await db.refresh(vm)
    return VMResponse.model_validate(vm, from_attributes=True)


# ── Delete ─────────────────────────────────────────────────────────────────────

@router.delete(
    "/{vm_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[TenantAdminUp],
    summary="Delete VM and its disks",
)
async def delete_vm(vm_id: str, db: TenantDB, user: CurrentUser) -> None:
    result = await db.execute(select(VM).where(VM.id == vm_id))
    vm = result.scalar_one_or_none()
    if vm is None:
        raise HTTPException(status_code=404, detail="VM not found")
    if vm.status == VMStatus.running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="VM must be stopped before deletion",
        )

    service = VMService(db)
    await service.destroy(vm)


# ── Power Actions ──────────────────────────────────────────────────────────────

@router.post(
    "/{vm_id}/actions",
    response_model=VMResponse,
    dependencies=[OperatorUp],
    summary="Perform a power action on a VM (start, stop, reboot, pause, resume)",
)
async def vm_action(vm_id: str, body: VMActionRequest, db: TenantDB, user: CurrentUser) -> VMResponse:
    result = await db.execute(select(VM).where(VM.id == vm_id, VM.status != VMStatus.deleted))
    vm = result.scalar_one_or_none()
    if vm is None:
        raise HTTPException(status_code=404, detail="VM not found")

    service = VMService(db)
    vm = await service.perform_action(vm, body.action, force=body.force)
    return VMResponse.model_validate(vm, from_attributes=True)


# ── Metrics ────────────────────────────────────────────────────────────────────

@router.get("/{vm_id}/metrics", summary="Real-time CPU, RAM, disk I/O for a running VM")
async def vm_metrics(vm_id: str, db: TenantDB, user: CurrentUser) -> dict:
    result = await db.execute(select(VM).where(VM.id == vm_id))
    vm = result.scalar_one_or_none()
    if vm is None or vm.status != VMStatus.running:
        raise HTTPException(status_code=404, detail="VM not found or not running")

    service = VMService(db)
    return await service.get_metrics(vm)
