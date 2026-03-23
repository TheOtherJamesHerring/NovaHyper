"""RLS policies, audit trigger, updated_at trigger

Revision ID: 0002
Revises: 0001
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TENANT_TABLES = ["users", "api_keys", "vms", "backup_jobs", "backup_manifests", "networks"]


def upgrade() -> None:
    # updated_at trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_vms_updated_at
        BEFORE UPDATE ON vms
        FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)

    # audit immutability
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_log_immutable()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log rows are immutable. Action: %, Table: %', TG_OP, TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_audit_log_immutable
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION audit_log_immutable()
    """)

    # RLS per tenant-scoped table
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_tenant_select ON {table} FOR SELECT
            USING (tenant_id::text = current_tenant_id())
        """)
        op.execute(f"""
            CREATE POLICY {table}_tenant_insert ON {table} FOR INSERT
            WITH CHECK (tenant_id::text = current_tenant_id())
        """)
        op.execute(f"""
            CREATE POLICY {table}_tenant_update ON {table} FOR UPDATE
            USING (tenant_id::text = current_tenant_id())
            WITH CHECK (tenant_id::text = current_tenant_id())
        """)
        op.execute(f"""
            CREATE POLICY {table}_tenant_delete ON {table} FOR DELETE
            USING (tenant_id::text = current_tenant_id())
        """)
        # MSP admin bypass — app sets tenant_id='MSP_ADMIN_BYPASS'
        op.execute(f"""
            CREATE POLICY {table}_msp_admin ON {table} FOR ALL
            USING (current_tenant_id() = 'MSP_ADMIN_BYPASS')
            WITH CHECK (true)
        """)

    # disks uses a JOIN-based policy (no direct tenant_id column)
    op.execute("ALTER TABLE disks ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY disks_via_vm ON disks FOR ALL
        USING (vm_id IN (SELECT id FROM vms WHERE tenant_id::text = current_tenant_id()))
        WITH CHECK (vm_id IN (SELECT id FROM vms WHERE tenant_id::text = current_tenant_id()))
    """)
    op.execute("""
        CREATE POLICY disks_msp_admin ON disks FOR ALL
        USING (current_tenant_id() = 'MSP_ADMIN_BYPASS')
        WITH CHECK (true)
    """)


def downgrade() -> None:
    for table in TENANT_TABLES:
        for policy in ["select", "insert", "update", "delete", "msp_admin"]:
            op.execute(f"DROP POLICY IF EXISTS {table}_tenant_{policy} ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_msp_admin ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS disks_via_vm ON disks")
    op.execute("DROP POLICY IF EXISTS disks_msp_admin ON disks")
    op.execute("ALTER TABLE disks DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_log_immutable ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS audit_log_immutable()")
    op.execute("DROP TRIGGER IF EXISTS trg_vms_updated_at ON vms")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")
