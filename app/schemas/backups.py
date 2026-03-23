"""app/schemas/backups.py — Backup job request/response schemas."""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict
from app.models import BackupStatus, BackupType


class LooseModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class BackupJobCreate(StrictModel):
    vm_id: str
    job_type: BackupType = BackupType.incremental
    disk_ids: list[str] | None = None


class BackupRestoreRequest(StrictModel):
    manifest_id: str
    target_vm_id: str | None = None
    target_storage_pool_id: str | None = None


class BackupJobResponse(LooseModel):
    id: str
    vm_id: str
    tenant_id: str
    job_type: BackupType
    status: BackupStatus
    parent_job_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    bytes_read: int = 0
    bytes_written: int = 0
    error_message: str | None = None
    created_at: datetime

    @property
    def dedup_ratio(self) -> float | None:
        if self.bytes_read and self.bytes_written:
            return round(self.bytes_read / self.bytes_written, 2)
        return None

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


class BackupManifestResponse(LooseModel):
    id: str
    job_id: str
    tenant_id: str
    vm_config_snapshot: dict[str, Any] = {}
    size_before_bytes: int = 0
    size_after_bytes: int = 0
    parent_manifest_id: str | None = None
    created_at: datetime
    chunk_count: int = 0

    @property
    def dedup_ratio(self) -> float:
        if self.size_after_bytes:
            return round(self.size_before_bytes / self.size_after_bytes, 2)
        return 1.0
