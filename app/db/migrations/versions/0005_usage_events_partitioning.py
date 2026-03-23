"""Automated usage_events partition management.

Revision ID: 0005
Revises: 0004
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS partition_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            table_name VARCHAR(128) NOT NULL,
            partition_name VARCHAR(128) NOT NULL,
            range_start DATE NOT NULL,
            range_end DATE NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (table_name, partition_name)
        )
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION create_monthly_partition(part_year int, part_month int)
        RETURNS VOID AS $$
        DECLARE
            partition_start DATE;
            partition_end DATE;
            partition_name TEXT;
        BEGIN
            partition_start := make_date(part_year, part_month, 1);
            partition_end := (partition_start + INTERVAL '1 month')::date;
            partition_name := format('usage_events_%s', to_char(partition_start, 'YYYY_MM'));

            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS %I PARTITION OF usage_events FOR VALUES FROM (%L) TO (%L)',
                partition_name,
                partition_start,
                partition_end
            );

            INSERT INTO partition_log (table_name, partition_name, range_start, range_end)
            VALUES ('usage_events', partition_name, partition_start, partition_end)
            ON CONFLICT (table_name, partition_name) DO NOTHING;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute("SELECT create_monthly_partition(2026, 5)")
    op.execute("SELECT create_monthly_partition(2026, 6)")
    op.execute("SELECT create_monthly_partition(2026, 7)")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS create_monthly_partition(int, int)")
    op.execute("DROP TABLE IF EXISTS partition_log")
