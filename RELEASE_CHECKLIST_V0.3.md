# NovaHyper v0.3 Release Commit/Tag Checklist

## Scope Lock

- [ ] Confirm all v0.3 features are merged into `main`.
- [ ] Confirm migration chain is linear through `0008`.
- [ ] Confirm no TODOs/blockers remain in tenant lifecycle, partition manager, and metering paths.

## Validation Gate

- [ ] Run full tests: `python -m pytest tests/`
- [ ] Verify expected result: all tests pass.
- [ ] Run migrations on a clean/staging DB: `alembic upgrade head`
- [ ] Verify app boots with startup services (partition manager + metering).
- [ ] Smoke test API auth + tenant endpoints + VM listing.

## Legacy Metering Deprecation Gate

- [ ] Confirm active runtime path uses `app/services/metering.py`.
- [ ] Confirm `app/services/usage_metering.py` is compatibility-only and emits deprecation warnings.
- [ ] Confirm no production imports depend on legacy class/function names.

## Release Commit Prep

- [ ] Review working tree: `git status`
- [ ] Review final diff: `git diff --stat` and `git diff`
- [ ] Stage release content: `git add -A`
- [ ] Create release commit:
  - Example: `git commit -m "release(v0.3): multi-tenant lifecycle, partition manager, batch metering"`

## Tagging

- [ ] Create annotated tag:
  - `git tag -a v0.3.0 -m "NovaHyper v0.3.0"`
- [ ] Verify tag:
  - `git show v0.3.0 --no-patch`

## Publish

- [ ] Push commit(s): `git push origin main`
- [ ] Push tag: `git push origin v0.3.0`
- [ ] Confirm tag exists on remote and points to intended commit.

## Release Notes (GitHub)

- [ ] Title: `NovaHyper v0.3.0`
- [ ] Include highlights:
  - Multi-tenant MSP admin endpoints and lifecycle actions.
  - Forced RLS + runtime role enforcement.
  - Automated usage partition provisioning + background manager.
  - Batched usage metering service.
  - Integration tests for RLS and tenant lifecycle.
- [ ] Add migration/upgrade note: run `alembic upgrade head` before deployment.

## Rollout Safety

- [ ] Deploy to staging and observe logs for 15-30 minutes.
- [ ] Verify no partition creation failures and no metering insert errors.
- [ ] Verify suspended tenant enforcement returns 403 for tenant-scoped APIs.
- [ ] Promote to production with maintenance window/rollback plan.

## Rollback Plan

- [ ] If deployment fails before traffic switch: revert image/app release and keep DB untouched.
- [ ] If DB migration-related issue occurs: evaluate `alembic downgrade -1` only if safe for data shape.
- [ ] If runtime issue after cutover: revert app to prior tag, keep DB at head when possible, and patch-forward.
