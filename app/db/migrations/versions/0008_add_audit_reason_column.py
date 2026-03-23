"""Add reason column to audit_log.

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_log", sa.Column("reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("audit_log", "reason")
