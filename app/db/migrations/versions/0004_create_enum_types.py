"""Create PostgreSQL enum types to match ORM models

Revision ID: 0004
Revises: 0003
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create all enum types
    op.execute("CREATE TYPE plantier AS ENUM ('starter', 'pro', 'enterprise')")
    op.execute("CREATE TYPE tenantstatus AS ENUM ('active', 'suspended', 'cancelled')")
    op.execute("CREATE TYPE userrole AS ENUM ('msp_admin', 'tenant_admin', 'operator', 'viewer')")
    op.execute("CREATE TYPE vmstatus AS ENUM ('provisioning', 'running', 'stopped', 'paused', 'error', 'deleted')")
    op.execute("CREATE TYPE diskformat AS ENUM ('qcow2', 'raw')")
    op.execute("CREATE TYPE storagetype AS ENUM ('zfs', 'ceph_rbd', 'nfs', 'lvm')")
    op.execute("CREATE TYPE backuptype AS ENUM ('full', 'incremental')")
    op.execute("CREATE TYPE backupstatus AS ENUM ('queued', 'running', 'success', 'failed', 'cancelled')")

    # Drop defaults, alter types, restore defaults
    op.execute("ALTER TABLE tenants ALTER COLUMN plan_tier DROP DEFAULT")
    op.execute("ALTER TABLE tenants ALTER COLUMN plan_tier TYPE plantier USING plan_tier::plantier")
    op.execute("ALTER TABLE tenants ALTER COLUMN plan_tier SET DEFAULT 'starter'::plantier")

    op.execute("ALTER TABLE tenants ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE tenants ALTER COLUMN status TYPE tenantstatus USING status::tenantstatus")
    op.execute("ALTER TABLE tenants ALTER COLUMN status SET DEFAULT 'active'::tenantstatus")

    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::userrole")
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'viewer'::userrole")

    op.execute("ALTER TABLE vms ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE vms ALTER COLUMN status TYPE vmstatus USING status::vmstatus")
    op.execute("ALTER TABLE vms ALTER COLUMN status SET DEFAULT 'provisioning'::vmstatus")

    op.execute("ALTER TABLE disks ALTER COLUMN disk_format DROP DEFAULT")
    op.execute("ALTER TABLE disks ALTER COLUMN disk_format TYPE diskformat USING disk_format::diskformat")
    op.execute("ALTER TABLE disks ALTER COLUMN disk_format SET DEFAULT 'qcow2'::diskformat")

    op.execute("ALTER TABLE storage_pools ALTER COLUMN pool_type TYPE storagetype USING pool_type::storagetype")

    op.execute("ALTER TABLE backup_jobs ALTER COLUMN job_type TYPE backuptype USING job_type::backuptype")

    op.execute("ALTER TABLE backup_jobs ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE backup_jobs ALTER COLUMN status TYPE backupstatus USING status::backupstatus")
    op.execute("ALTER TABLE backup_jobs ALTER COLUMN status SET DEFAULT 'queued'::backupstatus")


def downgrade() -> None:
    # Revert columns back to VARCHAR, restoring original defaults
    op.execute("ALTER TABLE tenants ALTER COLUMN plan_tier DROP DEFAULT")
    op.execute("ALTER TABLE tenants ALTER COLUMN plan_tier TYPE VARCHAR(32) USING plan_tier::text")
    op.execute("ALTER TABLE tenants ALTER COLUMN plan_tier SET DEFAULT 'starter'")

    op.execute("ALTER TABLE tenants ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE tenants ALTER COLUMN status TYPE VARCHAR(32) USING status::text")
    op.execute("ALTER TABLE tenants ALTER COLUMN status SET DEFAULT 'active'")

    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE VARCHAR(32) USING role::text")
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'viewer'")

    op.execute("ALTER TABLE vms ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE vms ALTER COLUMN status TYPE VARCHAR(32) USING status::text")
    op.execute("ALTER TABLE vms ALTER COLUMN status SET DEFAULT 'provisioning'")

    op.execute("ALTER TABLE disks ALTER COLUMN disk_format DROP DEFAULT")
    op.execute("ALTER TABLE disks ALTER COLUMN disk_format TYPE VARCHAR(16) USING disk_format::text")
    op.execute("ALTER TABLE disks ALTER COLUMN disk_format SET DEFAULT 'qcow2'")

    op.execute("ALTER TABLE storage_pools ALTER COLUMN pool_type TYPE VARCHAR(32) USING pool_type::text")

    op.execute("ALTER TABLE backup_jobs ALTER COLUMN job_type TYPE VARCHAR(32) USING job_type::text")

    op.execute("ALTER TABLE backup_jobs ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE backup_jobs ALTER COLUMN status TYPE VARCHAR(32) USING status::text")
    op.execute("ALTER TABLE backup_jobs ALTER COLUMN status SET DEFAULT 'queued'")

    # Drop enum types in reverse order
    op.execute("DROP TYPE IF EXISTS backupstatus")
    op.execute("DROP TYPE IF EXISTS backuptype")
    op.execute("DROP TYPE IF EXISTS storagetype")
    op.execute("DROP TYPE IF EXISTS diskformat")
    op.execute("DROP TYPE IF EXISTS vmstatus")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS tenantstatus")
    op.execute("DROP TYPE IF EXISTS plantier")