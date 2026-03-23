"""
app/schemas/
------------
Pydantic v2 request / response models.

Rules:
- Request models validate input and strip unknown fields (model_config extra="forbid").
- Response models are permissive (extra="ignore") to safely evolve ORM models.
- IDs are always strings (UUID) — never expose raw int sequences.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import BackupStatus, BackupType, DiskFormat, PlanTier, StorageType, UserRole, VMStatus


# ── Base ───────────────────────────────────────────────────────────────────────

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LooseModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ── Auth ───────────────────────────────────────────────────────────────────────

class LoginRequest(StrictModel):
    email: EmailStr
    password: str = Field(min_length=8)


class TokenResponse(LooseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(StrictModel):
    refresh_token: str


# ── Tenants ────────────────────────────────────────────────────────────────────

class TenantCreate(StrictModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9-]+$")
    plan_tier: PlanTier = PlanTier.starter
    admin_email: EmailStr
    admin_password: str = Field(min_length=12)
    admin_full_name: str | None = None


class TenantResponse(LooseModel):
    id: str
    name: str
    slug: str
    plan_tier: PlanTier
    status: str
    created_at: datetime


# ── Users ──────────────────────────────────────────────────────────────────────

class UserCreate(StrictModel):
    email: EmailStr
    password: str = Field(min_length=12)
    full_name: str | None = None
    role: UserRole = UserRole.viewer


class UserResponse(LooseModel):
    id: str
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool
    created_at: datetime


# ── VMs ────────────────────────────────────────────────────────────────────────

class DiskSpec(StrictModel):
    size_gb: int = Field(ge=10, le=65536)
    disk_format: DiskFormat = DiskFormat.qcow2
    storage_pool_id: str


class VMCreate(StrictModel):
    name: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, max_length=512)
    vcpus: int = Field(ge=1, le=256)
    ram_mb: int = Field(ge=512, le=2097152)   # 512 MB – 2 TB
    os_type: str = Field(pattern=r"^(windows|linux|bsd|other)$")
    os_variant: str | None = Field(default=None, max_length=128)
    host_id: str
    disks: list[DiskSpec] = Field(min_length=1, max_length=8)
    network_id: str | None = None
    iso_path: str | None = None
    backup_policy: dict[str, Any] = Field(default_factory=dict)
    tags: dict[str, str] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def name_not_reserved(cls, v: str) -> str:
        reserved = {"admin", "root", "localhost", "novahyper"}
        if v.lower() in reserved:
            raise ValueError(f"Name '{v}' is reserved")
        return v


class VMUpdate(StrictModel):
    description: str | None = None
    vcpus: int | None = Field(default=None, ge=1, le=256)
    ram_mb: int | None = Field(default=None, ge=512, le=2097152)
    backup_policy: dict[str, Any] | None = None
    tags: dict[str, str] | None = None


class DiskResponse(LooseModel):
    id: str
    device_name: str
    path: str
    size_gb: int
    disk_format: DiskFormat
    backup_enabled: bool
    bitmap_name: str | None


class VMResponse(LooseModel):
    id: str
    name: str
    description: str | None
    status: VMStatus
    vcpus: int
    ram_mb: int
    os_type: str
    os_variant: str | None
    host_id: str | None
    libvirt_uuid: str | None
    disks: list[DiskResponse]
    backup_policy: dict[str, Any]
    tags: dict[str, str]
    created_at: datetime
    updated_at: datetime

    @property
    def ram_gb(self) -> float:
        return round(self.ram_mb / 1024, 1)


class VMActionRequest(StrictModel):
    action: str = Field(pattern=r"^(start|stop|reboot|pause|resume|reset)$")
    force: bool = False  # Force stop without graceful shutdown


# ── Backups ────────────────────────────────────────────────────────────────────

class BackupJobCreate(StrictModel):
    vm_id: str
    job_type: BackupType = BackupType.incremental


class BackupJobResponse(LooseModel):
    id: str
    vm_id: str
    job_type: BackupType
    status: BackupStatus
    started_at: datetime | None
    finished_at: datetime | None
    bytes_read: int
    bytes_written: int
    error_message: str | None
    created_at: datetime

    @property
    def dedup_ratio(self) -> float | None:
        if self.bytes_read and self.bytes_written:
            return round(self.bytes_read / self.bytes_written, 2)
        return None


# ── Pagination ─────────────────────────────────────────────────────────────────

class PaginatedResponse[T](LooseModel):
    items: list[T]
    total: int
    page: int
    page_size: int
    has_more: bool


from app.schemas.audit import AuditEventResponse, AuditVerifyResponse
