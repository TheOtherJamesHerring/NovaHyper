"""app/schemas/tenants.py — Tenant management request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import PlanTier, TenantStatus, UserRole


class LooseModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TenantCreateRequest(StrictModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9-]+$")
    plan_tier: PlanTier = PlanTier.starter
    max_vcpus: int = Field(default=0, ge=0)
    max_ram_gb: int = Field(default=0, ge=0)
    max_storage_gb: int = Field(default=0, ge=0)
    max_backup_gb: int = Field(default=0, ge=0)
    admin_email: EmailStr
    admin_password: str = Field(min_length=12)
    admin_full_name: str | None = Field(default=None, max_length=255)


class TenantUpdateRequest(StrictModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    plan_tier: PlanTier | None = None
    max_vcpus: int | None = Field(default=None, ge=0)
    max_ram_gb: int | None = Field(default=None, ge=0)
    max_storage_gb: int | None = Field(default=None, ge=0)
    max_backup_gb: int | None = Field(default=None, ge=0)


class TenantSuspendRequest(StrictModel):
    reason: str = Field(min_length=3, max_length=512)


class TenantReinstateRequest(StrictModel):
    reason: str | None = Field(default=None, max_length=512)


class TenantUserInviteRequest(StrictModel):
    email: EmailStr
    password: str = Field(min_length=12)
    full_name: str | None = Field(default=None, max_length=255)
    role: UserRole = UserRole.viewer
    is_active: bool = True


class TenantResponse(LooseModel):
    id: str
    name: str
    slug: str
    plan_tier: PlanTier
    status: TenantStatus
    max_vcpus: int
    max_ram_gb: int
    max_storage_gb: int
    max_backup_gb: int
    created_at: datetime
    updated_at: datetime


class TenantDetailResponse(TenantResponse):
    user_count: int
    vm_count: int


class TenantUserResponse(LooseModel):
    id: str
    tenant_id: str
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool
    created_at: datetime