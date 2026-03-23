"""
0003_bootstrap_admin.py
-----------------------
Seeds the platform root MSP tenant and its first admin user.

Values come from environment variables:
    BOOTSTRAP_ADMIN_EMAIL     (required — skipped if blank)
    BOOTSTRAP_ADMIN_PASSWORD  (required — skipped if blank)

Idempotent: skips if a tenant with slug='platform' already exists.
Safe to run in CI against a fresh DB.
"""
import os
import uuid
from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    email    = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip()
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "").strip()

    if not email or not password:
        print("  [0003] BOOTSTRAP_ADMIN_EMAIL / PASSWORD not set — skipping seed")
        return

    conn = op.get_bind()

    # Check if already seeded
    existing = conn.execute(
        text("SELECT id FROM tenants WHERE slug = 'platform' LIMIT 1")
    ).fetchone()
    if existing:
        print("  [0003] Platform tenant already exists — skipping seed")
        return

# Hash the password using bcrypt directly (passlib has version compat issues)
    import bcrypt as _bcrypt
    hashed = _bcrypt.hashpw(password.encode("utf-8")[:72], _bcrypt.gensalt(12)).decode("utf-8")

    tenant_id = str(uuid.uuid4())
    user_id   = str(uuid.uuid4())
    now       = datetime.now(UTC)

    conn.execute(text("""
        INSERT INTO tenants (id, name, slug, plan_tier, status, created_at, updated_at)
        VALUES (:id, :name, :slug, 'enterprise', 'active', :now, :now)
    """), {"id": tenant_id, "name": "Platform MSP", "slug": "platform", "now": now})

    conn.execute(text("""
        INSERT INTO users (id, tenant_id, email, hashed_password, full_name, role, is_active, created_at)
        VALUES (:id, :tid, :email, :pw, 'Platform Admin', 'msp_admin', true, :now)
    """), {"id": user_id, "tid": tenant_id, "email": email, "pw": hashed, "now": now})

    print(f"  [0003] Seeded platform tenant ({tenant_id}) and admin user ({email})")


def downgrade() -> None:
    conn = op.get_bind()
    row = conn.execute(
        text("SELECT id FROM tenants WHERE slug = 'platform' LIMIT 1")
    ).fetchone()
    if row:
        tenant_id = row[0]
        conn.execute(text("DELETE FROM users   WHERE tenant_id = :tid"), {"tid": tenant_id})
        conn.execute(text("DELETE FROM tenants WHERE id = :tid"),        {"tid": tenant_id})
        print(f"  [0003] Removed platform tenant {tenant_id}")
