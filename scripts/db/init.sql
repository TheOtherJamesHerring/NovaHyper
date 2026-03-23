-- scripts/db/init.sql
-- Applied once at container startup. Alembic handles schema evolution.

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Row-Level Security setup ───────────────────────────────────────────────
-- All tenant-scoped tables get RLS enabled after Alembic creates them.
-- This script sets up the current_tenant() helper used by all policies.

CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS TEXT AS $$
  SELECT NULLIF(current_setting('app.tenant_id', true), '')
$$ LANGUAGE SQL STABLE;

-- ── Audit log protection trigger ──────────────────────────────────────────
-- Prevents any UPDATE or DELETE on audit_log rows.
CREATE OR REPLACE FUNCTION audit_log_immutable() RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'audit_log rows are immutable';
END;
$$ LANGUAGE plpgsql;

-- The trigger is attached to the table after Alembic creates it.
-- See migration: 0002_add_audit_rls.py

-- ── Usage events partitioning ─────────────────────────────────────────────
-- usage_events is range-partitioned by recorded_at (monthly).
-- Partitions are created by the application's monthly scheduler.
-- Example partition (created programmatically):
--   CREATE TABLE usage_events_2026_03
--     PARTITION OF usage_events
--     FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

-- ── Index additions (performance tuning) ─────────────────────────────────
-- Added here rather than in Alembic for clarity; Alembic will detect them
-- as already-existing on the next autogenerate run.

-- End of init.sql
