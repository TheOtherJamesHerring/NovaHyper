"""
app/models/
-----------
SQLAlchemy ORM models.  Every tenant-scoped table has a tenant_id column
and a corresponding RLS policy (applied via migration, not here).

Naming conventions:
  - Primary keys are UUIDs generated server-side.
  - Timestamps use timezone-aware UTC datetimes.
  - JSONB columns store flexible/evolving data (vm config, chunk refs).
"""
import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(UTC)


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


# ── Enums ──────────────────────────────────────────────────────────────────────

class PlanTier(str, enum.Enum):
    starter = "starter"
    pro = "pro"
    enterprise = "enterprise"


class TenantStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"
    cancelled = "cancelled"


class UserRole(str, enum.Enum):
    msp_admin = "msp_admin"      # Full platform access across all tenants
    tenant_admin = "tenant_admin" # Full access within own tenant
    operator = "operator"         # Manage VMs, trigger backups
    viewer = "viewer"             # Read-only


class VMStatus(str, enum.Enum):
    provisioning = "provisioning"
    running = "running"
    stopped = "stopped"
    paused = "paused"
    error = "error"
    deleted = "deleted"


class DiskFormat(str, enum.Enum):
    qcow2 = "qcow2"
    raw = "raw"


class StorageType(str, enum.Enum):
    zfs = "zfs"
    ceph_rbd = "ceph_rbd"
    nfs = "nfs"
    lvm = "lvm"


class BackupType(str, enum.Enum):
    full = "full"
    incremental = "incremental"


class BackupStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"


# ── Tenants ────────────────────────────────────────────────────────────────────

class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    plan_tier: Mapped[PlanTier] = mapped_column(Enum(PlanTier), default=PlanTier.starter)
    status: Mapped[TenantStatus] = mapped_column(Enum(TenantStatus), default=TenantStatus.active)
    # Billing limits (0 = unlimited)
    max_vcpus: Mapped[int] = mapped_column(Integer, default=0)
    max_ram_gb: Mapped[int] = mapped_column(Integer, default=0)
    max_storage_gb: Mapped[int] = mapped_column(Integer, default=0)
    max_backup_gb: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    users: Mapped[list["User"]] = relationship(back_populates="tenant", lazy="selectin")
    vms: Mapped[list["VM"]] = relationship(back_populates="tenant", lazy="noload")


# ── Users ──────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(72), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.viewer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    mfa_secret: Mapped[str | None] = mapped_column(String(64))  # TOTP secret (encrypted at rest)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    tenant: Mapped["Tenant"] = relationship(back_populates="users")

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    scopes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ── Infrastructure ─────────────────────────────────────────────────────────────

class KVMHost(Base):
    """Physical or virtual KVM compute node."""
    __tablename__ = "kvm_hosts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    libvirt_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    vcpu_total: Mapped[int] = mapped_column(Integer, default=0)
    vcpu_used: Mapped[int] = mapped_column(Integer, default=0)
    ram_total_gb: Mapped[int] = mapped_column(Integer, default=0)
    ram_used_gb: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    vms: Mapped[list["VM"]] = relationship(back_populates="host", lazy="noload")
    storage_pools: Mapped[list["StoragePool"]] = relationship(back_populates="host", lazy="noload")


class StoragePool(Base):
    __tablename__ = "storage_pools"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    host_id: Mapped[str | None] = mapped_column(ForeignKey("kvm_hosts.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    pool_type: Mapped[StorageType] = mapped_column(Enum(StorageType), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    capacity_gb: Mapped[int] = mapped_column(Integer, default=0)
    used_gb: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    host: Mapped["KVMHost | None"] = relationship(back_populates="storage_pools")


# ── Virtual Machines ───────────────────────────────────────────────────────────

class VM(Base):
    __tablename__ = "vms"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    host_id: Mapped[str | None] = mapped_column(ForeignKey("kvm_hosts.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[VMStatus] = mapped_column(Enum(VMStatus), default=VMStatus.provisioning)
    vcpus: Mapped[int] = mapped_column(Integer, nullable=False)
    ram_mb: Mapped[int] = mapped_column(Integer, nullable=False)   # Store MB for precision
    os_type: Mapped[str] = mapped_column(String(64), nullable=False)  # "windows", "linux"
    os_variant: Mapped[str | None] = mapped_column(String(128))    # "win2022", "ubuntu22.04"
    libvirt_uuid: Mapped[str | None] = mapped_column(UUID(as_uuid=False), unique=True)
    # Full libvirt domain XML — preserved for migration and audit
    libvirt_xml: Mapped[str | None] = mapped_column(Text)
    # Flexible metadata: tags, notes, custom fields
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Backup policy reference
    backup_policy: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    tenant: Mapped["Tenant"] = relationship(back_populates="vms")
    host: Mapped["KVMHost | None"] = relationship(back_populates="vms")
    disks: Mapped[list["Disk"]] = relationship(back_populates="vm", lazy="selectin", cascade="all, delete-orphan")
    backup_jobs: Mapped[list["BackupJob"]] = relationship(back_populates="vm", lazy="noload")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_vms_tenant_name"),
        Index("ix_vms_tenant_status", "tenant_id", "status"),
    )


class Disk(Base):
    __tablename__ = "disks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    vm_id: Mapped[str] = mapped_column(ForeignKey("vms.id", ondelete="CASCADE"), nullable=False)
    storage_pool_id: Mapped[str | None] = mapped_column(ForeignKey("storage_pools.id", ondelete="SET NULL"))
    device_name: Mapped[str] = mapped_column(String(16), default="vda")  # vda, vdb, ...
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    size_gb: Mapped[int] = mapped_column(Integer, nullable=False)
    disk_format: Mapped[DiskFormat] = mapped_column(Enum(DiskFormat), default=DiskFormat.qcow2)
    backup_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # SHA256 of the current dirty bitmap (null if no bitmap active)
    bitmap_name: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    vm: Mapped["VM"] = relationship(back_populates="disks")


# ── Backups ────────────────────────────────────────────────────────────────────

class BackupJob(Base):
    __tablename__ = "backup_jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    vm_id: Mapped[str] = mapped_column(ForeignKey("vms.id", ondelete="CASCADE"), nullable=False)
    job_type: Mapped[BackupType] = mapped_column(Enum(BackupType), nullable=False)
    status: Mapped[BackupStatus] = mapped_column(Enum(BackupStatus), default=BackupStatus.queued)
    parent_job_id: Mapped[str | None] = mapped_column(ForeignKey("backup_jobs.id"))  # For incrementals
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    # Sizes in bytes
    bytes_read: Mapped[int] = mapped_column(BigInteger, default=0)
    bytes_written: Mapped[int] = mapped_column(BigInteger, default=0)  # post-dedup
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    vm: Mapped["VM"] = relationship(back_populates="backup_jobs")
    manifest: Mapped["BackupManifest | None"] = relationship(back_populates="job", uselist=False)

    __table_args__ = (
        Index("ix_backup_jobs_vm_status", "vm_id", "status"),
        Index("ix_backup_jobs_tenant_created", "tenant_id", "created_at"),
    )


class BackupManifest(Base):
    """
    Point-in-time record of a completed backup.
    ``chunk_refs`` is a JSONB array of {hash, offset, length} objects.
    This is the restore index — given a manifest, we can reconstruct the disk.
    """
    __tablename__ = "backup_manifests"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("backup_jobs.id", ondelete="CASCADE"), unique=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    vm_config_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)   # VM state at backup time
    chunk_refs: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)     # [{hash, offset, length}]
    size_before_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    size_after_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    parent_manifest_id: Mapped[str | None] = mapped_column(ForeignKey("backup_manifests.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    job: Mapped["BackupJob"] = relationship(back_populates="manifest")


# ── Dedup Chunk Registry ───────────────────────────────────────────────────────

class Chunk(Base):
    """
    One row per unique chunk in the dedup store.
    ref_count is incremented on write, decremented on manifest deletion.
    GC deletes rows and files where ref_count = 0.
    """
    __tablename__ = "chunks"

    sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    store_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    compressed_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    ref_count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        Index("ix_chunks_ref_count", "ref_count"),   # GC query: WHERE ref_count = 0
    )


# ── Usage Metering ─────────────────────────────────────────────────────────────

class UsageEvent(Base):
    """
    Immutable metering stream.  Partitioned by month in PostgreSQL via
    declarative partitioning on recorded_at (handled in migration, not here).
    """
    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)  # "vm_vcpu", "backup_gb"
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    quantity: Mapped[float] = mapped_column(nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        Index("ix_usage_events_tenant_ts", "tenant_id", "recorded_at"),
    )


# ── Audit Log ──────────────────────────────────────────────────────────────────

class AuditLog(Base):
    """
    Append-only.  A PostgreSQL trigger prevents UPDATE and DELETE.
    payload_hash is SHA-256 of the serialised operation parameters.
    """
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str | None] = mapped_column(String(36))  # null for platform-level events
    user_id: Mapped[str | None] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(128), nullable=False)   # "vm.create", "backup.delete"
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(128))
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        Index("ix_audit_tenant_ts", "tenant_id", "ts"),
    )
