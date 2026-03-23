"""Create non-superuser runtime role for tenant-scoped RLS queries.

Revision ID: 0007
Revises: 0006
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

RLS_RUNTIME_ROLE = "novahyper_rls_runtime"


def upgrade() -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{RLS_RUNTIME_ROLE}') THEN
            CREATE ROLE {RLS_RUNTIME_ROLE} NOLOGIN NOSUPERUSER NOBYPASSRLS;
          END IF;
        END
        $$;
        """
    )
    op.execute(f"GRANT {RLS_RUNTIME_ROLE} TO CURRENT_USER")
    op.execute(f"GRANT USAGE ON SCHEMA public TO {RLS_RUNTIME_ROLE}")
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {RLS_RUNTIME_ROLE}"
    )
    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {RLS_RUNTIME_ROLE}")
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {RLS_RUNTIME_ROLE}"
    )
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {RLS_RUNTIME_ROLE}"
    )


def downgrade() -> None:
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM {RLS_RUNTIME_ROLE}"
    )
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE USAGE, SELECT ON SEQUENCES FROM {RLS_RUNTIME_ROLE}"
    )
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {RLS_RUNTIME_ROLE}")
    op.execute(f"REVOKE SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM {RLS_RUNTIME_ROLE}")
    op.execute(f"REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public FROM {RLS_RUNTIME_ROLE}")
    op.execute(f"REVOKE {RLS_RUNTIME_ROLE} FROM CURRENT_USER")
    op.execute(f"DROP ROLE IF EXISTS {RLS_RUNTIME_ROLE}")
