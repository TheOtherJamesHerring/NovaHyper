"""
app/api/v1/endpoints/backups.py
POST  /backups           — queue a backup job (publishes to NATS)
GET   /backups           — list jobs (filter by vm_id, status, type)
GET   /backups/{id}      — single job detail
DELETE /backups/{id}     — cancel queued/running job
GET   /backups/{id}/manifest — restore index
"""
import json
import uuid
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import desc, func, select

from app.core.deps import CurrentUser, OperatorUp, TenantDB
from app.models import BackupJob, BackupManifest, BackupStatus, BackupType, VM, VMStatus
from app.schemas import PaginatedResponse
from app.schemas.backups import BackupJobCreate, BackupJobResponse, BackupManifestResponse

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/backups", tags=["backups"])
SUBJECT_BACKUP_QUEUED = "backup.job.queued"


async def _publish_job(request: Request, job_id: str, vm_id: str, tenant_id: str, job_type: str) -> None:
    nc = getattr(request.app.state, "nats", None)
    if nc is None:
        log.warning("nats.unavailable", job_id=job_id)
        return
    payload = json.dumps({
        "job_id": job_id, "vm_id": vm_id, "tenant_id": tenant_id,
        "job_type": job_type, "queued_at": datetime.now(UTC).isoformat(),
    }).encode()
    await nc.publish(SUBJECT_BACKUP_QUEUED, payload)
    log.info("nats.published", subject=SUBJECT_BACKUP_QUEUED, job_id=job_id)


@router.post("", response_model=BackupJobResponse, status_code=201, dependencies=[OperatorUp])
async def create_backup_job(body: BackupJobCreate, request: Request, db: TenantDB, user: CurrentUser) -> BackupJobResponse:
    vm = (await db.execute(select(VM).where(VM.id == body.vm_id, VM.status != VMStatus.deleted))).scalar_one_or_none()
    if vm is None:
        raise HTTPException(404, "VM not found")
    if vm.status == VMStatus.provisioning:
        raise HTTPException(409, "VM is still provisioning")

    # Auto-promote to full if no prior full backup exists
    if body.job_type == BackupType.incremental:
        full_count = (await db.execute(
            select(func.count(BackupJob.id)).where(
                BackupJob.vm_id == body.vm_id,
                BackupJob.job_type == BackupType.full,
                BackupJob.status == BackupStatus.success,
            )
        )).scalar_one()
        if full_count == 0:
            body = body.model_copy(update={"job_type": BackupType.full})

    job = BackupJob(id=str(uuid.uuid4()), tenant_id=user.tenant_id, vm_id=body.vm_id,
                    job_type=body.job_type, status=BackupStatus.queued)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    await _publish_job(request, job.id, vm.id, user.tenant_id, job.job_type.value)
    log.info("backup.job.queued", job_id=job.id, vm_id=vm.id, type=job.job_type.value)
    return BackupJobResponse.model_validate(job, from_attributes=True)


@router.get("", response_model=PaginatedResponse[BackupJobResponse])
async def list_backup_jobs(
    db: TenantDB, user: CurrentUser,
    vm_id: str | None = Query(None),
    job_status: BackupStatus | None = Query(None, alias="status"),
    job_type: BackupType | None = Query(None, alias="type"),
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
) -> PaginatedResponse[BackupJobResponse]:
    q = select(BackupJob)
    if vm_id: q = q.where(BackupJob.vm_id == vm_id)
    if job_status: q = q.where(BackupJob.status == job_status)
    if job_type: q = q.where(BackupJob.job_type == job_type)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.order_by(desc(BackupJob.created_at)).offset((page-1)*page_size).limit(page_size)
    jobs = (await db.execute(q)).scalars().all()
    return PaginatedResponse(
        items=[BackupJobResponse.model_validate(j, from_attributes=True) for j in jobs],
        total=total, page=page, page_size=page_size, has_more=(page*page_size)<total,
    )


@router.get("/{job_id}", response_model=BackupJobResponse)
async def get_backup_job(job_id: str, db: TenantDB, user: CurrentUser) -> BackupJobResponse:
    job = (await db.execute(select(BackupJob).where(BackupJob.id == job_id))).scalar_one_or_none()
    if job is None:
        raise HTTPException(404, "Backup job not found")
    return BackupJobResponse.model_validate(job, from_attributes=True)


@router.delete("/{job_id}", status_code=204, dependencies=[OperatorUp])
async def cancel_backup_job(job_id: str, db: TenantDB, user: CurrentUser) -> None:
    job = (await db.execute(select(BackupJob).where(BackupJob.id == job_id))).scalar_one_or_none()
    if job is None:
        raise HTTPException(404, "Backup job not found")
    if job.status not in (BackupStatus.queued, BackupStatus.running):
        raise HTTPException(409, f"Cannot cancel job with status '{job.status.value}'")
    job.status = BackupStatus.cancelled
    job.finished_at = datetime.now(UTC)
    await db.commit()


@router.get("/{job_id}/manifest", response_model=BackupManifestResponse)
async def get_manifest(job_id: str, db: TenantDB, user: CurrentUser) -> BackupManifestResponse:
    manifest = (await db.execute(
        select(BackupManifest).where(BackupManifest.job_id == job_id)
    )).scalar_one_or_none()
    if manifest is None:
        raise HTTPException(404, "No manifest found — job may not be complete yet")
    resp = BackupManifestResponse.model_validate(manifest, from_attributes=True)
    return resp.model_copy(update={"chunk_count": len(manifest.chunk_refs or [])})
