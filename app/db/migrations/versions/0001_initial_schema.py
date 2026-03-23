"""Initial schema — all tables

Revision ID: 0001
Revises:
Create Date: 2026-03-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Extensions ────────────────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ── Helper function: current_tenant_id() ─────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS TEXT AS $$
          SELECT NULLIF(current_setting('app.tenant_id', true), '')
        $$ LANGUAGE SQL STABLE
    """)

    # ── tenants ───────────────────────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("plan_tier", sa.String(32), nullable=False, server_default="starter"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("max_vcpus", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_ram_gb", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_storage_gb", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_backup_gb", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=False),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("hashed_password", sa.String(72), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("role", sa.String(32), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("mfa_secret", sa.String(64)),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint("uq_users_tenant_email", "users", ["tenant_id", "email"])
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    # ── api_keys ──────────────────────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=False),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=False),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("scopes", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )

    # ── kvm_hosts ─────────────────────────────────────────────────────────────
    op.create_table(
        "kvm_hosts",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("hostname", sa.String(255), nullable=False, unique=True),
        sa.Column("ip_address", sa.String(45), nullable=False),
        sa.Column("libvirt_uri", sa.String(512), nullable=False),
        sa.Column("vcpu_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("vcpu_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ram_total_gb", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ram_used_gb", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )

    # ── storage_pools ─────────────────────────────────────────────────────────
    op.create_table(
        "storage_pools",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("host_id", UUID(as_uuid=False),
                  sa.ForeignKey("kvm_hosts.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("pool_type", sa.String(32), nullable=False),
        sa.Column("path", sa.String(1024), nullable=False),
        sa.Column("capacity_gb", sa.Integer, nullable=False, server_default="0"),
        sa.Column("used_gb", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )

    # ── vms ───────────────────────────────────────────────────────────────────
    op.create_table(
        "vms",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=False),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("host_id", UUID(as_uuid=False),
                  sa.ForeignKey("kvm_hosts.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("status", sa.String(32), nullable=False, server_default="provisioning"),
        sa.Column("vcpus", sa.Integer, nullable=False),
        sa.Column("ram_mb", sa.Integer, nullable=False),
        sa.Column("os_type", sa.String(64), nullable=False),
        sa.Column("os_variant", sa.String(128)),
        sa.Column("libvirt_uuid", UUID(as_uuid=False), unique=True),
        sa.Column("libvirt_xml", sa.Text),
        sa.Column("config", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("backup_policy", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint("uq_vms_tenant_name", "vms", ["tenant_id", "name"])
    op.create_index("ix_vms_tenant_status", "vms", ["tenant_id", "status"])

    # ── disks ─────────────────────────────────────────────────────────────────
    op.create_table(
        "disks",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("vm_id", UUID(as_uuid=False),
                  sa.ForeignKey("vms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("storage_pool_id", UUID(as_uuid=False),
                  sa.ForeignKey("storage_pools.id", ondelete="SET NULL")),
        sa.Column("device_name", sa.String(16), nullable=False, server_default="vda"),
        sa.Column("path", sa.String(1024), nullable=False),
        sa.Column("size_gb", sa.Integer, nullable=False),
        sa.Column("disk_format", sa.String(16), nullable=False, server_default="qcow2"),
        sa.Column("backup_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("bitmap_name", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_disks_vm_id", "disks", ["vm_id"])

    # ── backup_jobs ───────────────────────────────────────────────────────────
    op.create_table(
        "backup_jobs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=False),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vm_id", UUID(as_uuid=False),
                  sa.ForeignKey("vms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("parent_job_id", UUID(as_uuid=False),
                  sa.ForeignKey("backup_jobs.id")),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text),
        sa.Column("bytes_read", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("bytes_written", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_backup_jobs_vm_status", "backup_jobs", ["vm_id", "status"])
    op.create_index("ix_backup_jobs_tenant_created", "backup_jobs", ["tenant_id", "created_at"])

    # ── backup_manifests ──────────────────────────────────────────────────────
    op.create_table(
        "backup_manifests",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("job_id", UUID(as_uuid=False),
                  sa.ForeignKey("backup_jobs.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("tenant_id", UUID(as_uuid=False),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vm_config_snapshot", JSONB, nullable=False),
        sa.Column("chunk_refs", JSONB, nullable=False),
        sa.Column("size_before_bytes", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("size_after_bytes", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("parent_manifest_id", UUID(as_uuid=False),
                  sa.ForeignKey("backup_manifests.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )

    # ── chunks ────────────────────────────────────────────────────────────────
    op.create_table(
        "chunks",
        sa.Column("sha256", sa.String(64), primary_key=True),
        sa.Column("store_path", sa.String(1024), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("compressed_bytes", sa.Integer, nullable=False),
        sa.Column("ref_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_chunks_ref_count", "chunks", ["ref_count"])

    # ── usage_events (partitioned by month) ───────────────────────────────────
    op.execute("""
        CREATE TABLE usage_events (
            id          UUID NOT NULL DEFAULT gen_random_uuid(),
            tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            resource_type VARCHAR(64) NOT NULL,
            resource_id   VARCHAR(128) NOT NULL,
            quantity      DOUBLE PRECISION NOT NULL,
            unit          VARCHAR(32) NOT NULL,
            recorded_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        ) PARTITION BY RANGE (recorded_at)
    """)
    # Create current and next month partitions
    op.execute("""
        CREATE TABLE usage_events_2026_03
            PARTITION OF usage_events
            FOR VALUES FROM ('2026-03-01') TO ('2026-04-01')
    """)
    op.execute("""
        CREATE TABLE usage_events_2026_04
            PARTITION OF usage_events
            FOR VALUES FROM ('2026-04-01') TO ('2026-05-01')
    """)
    op.execute("""
        CREATE INDEX ix_usage_events_tenant_ts
            ON usage_events (tenant_id, recorded_at)
    """)

    # ── audit_log ─────────────────────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=False), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.String(36)),
        sa.Column("user_id", sa.String(36)),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(128)),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_audit_tenant_ts", "audit_log", ["tenant_id", "ts"])

    # ── networks ──────────────────────────────────────────────────────────────
    op.create_table(
        "networks",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=False),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("vlan_id", sa.Integer, nullable=False),
        sa.Column("cidr", sa.String(45)),
        sa.Column("gateway", sa.String(45)),
        sa.Column("dns_servers", JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )


def downgrade() -> None:
    op.drop_table("networks")
    op.drop_table("audit_log")
    op.execute("DROP TABLE IF EXISTS usage_events CASCADE")
    op.drop_table("chunks")
    op.drop_table("backup_manifests")
    op.drop_table("backup_jobs")
    op.drop_table("disks")
    op.drop_table("vms")
    op.drop_table("storage_pools")
    op.drop_table("kvm_hosts")
    op.drop_table("api_keys")
    op.drop_table("users")
    op.drop_table("tenants")
    op.execute("DROP FUNCTION IF EXISTS current_tenant_id()")
