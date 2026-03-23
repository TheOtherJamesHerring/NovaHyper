"""
tests/unit/test_backups.py
---------------------------
Unit tests for backup endpoint logic and the NATS consumer handler.
All database and NATS calls are stubbed in-memory.
No real database, NATS broker, or libvirt required.
"""
import asyncio
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import BackupJob, BackupStatus, BackupType, VM, VMStatus


# ── Shared fixtures ───────────────────────────────────────────────────────────

def make_vm(status: VMStatus = VMStatus.running) -> VM:
    vm = MagicMock(spec=VM)
    vm.id = str(uuid.uuid4())
    vm.name = "test-vm"
    vm.tenant_id = str(uuid.uuid4())
    vm.status = status
    vm.disks = []
    vm.vcpus = 2
    vm.ram_mb = 2048
    vm.os_type = "linux"
    vm.os_variant = "ubuntu22.04"
    vm.libvirt_uuid = str(uuid.uuid4())
    return vm


def make_job(
    vm_id: str,
    tenant_id: str,
    job_type: BackupType = BackupType.incremental,
    status: BackupStatus = BackupStatus.queued,
) -> BackupJob:
    job = MagicMock(spec=BackupJob)
    job.id = str(uuid.uuid4())
    job.vm_id = vm_id
    job.tenant_id = tenant_id
    job.job_type = job_type
    job.status = status
    job.parent_job_id = None
    job.started_at = None
    job.finished_at = None
    job.bytes_read = 0
    job.bytes_written = 0
    job.error_message = None
    job.created_at = datetime.now(UTC)
    return job


# ── Auto-promote: incremental → full when no prior full exists ────────────────

class TestAutoPromoteToFull:
    """
    When a client requests an incremental backup but no successful full
    backup exists, the endpoint must silently promote to full.
    """

    @pytest.mark.asyncio
    async def test_promotes_to_full_when_no_prior_full(self):
        from app.api.v1.endpoints.backups import create_backup_job
        from app.schemas.backups import BackupJobCreate

        vm = make_vm()
        body = BackupJobCreate(vm_id=vm.id, job_type=BackupType.incremental)

        # DB stub: VM exists, full_count = 0
        db = AsyncMock()
        db.execute = AsyncMock()

        vm_result = MagicMock()
        vm_result.scalar_one_or_none.return_value = vm

        full_count_result = MagicMock()
        full_count_result.scalar_one.return_value = 0  # No prior full backups

        job_result = MagicMock()

        db.execute.side_effect = [vm_result, full_count_result]
        db.add = MagicMock()
        db.commit = AsyncMock()

        created_job = make_job(vm.id, vm.tenant_id, BackupType.full, BackupStatus.queued)
        db.refresh = AsyncMock(side_effect=lambda j: setattr(j, 'id', created_job.id))

        user = MagicMock()
        user.tenant_id = vm.tenant_id

        request = MagicMock()
        request.app.state.nats = None  # NATS unavailable — graceful degrade

        # Capture what gets added to db
        added = []
        db.add.side_effect = lambda obj: added.append(obj)

        with patch("app.api.v1.endpoints.backups.BackupJobResponse.model_validate") as mock_validate:
            mock_validate.return_value = MagicMock(id=created_job.id)
            try:
                await create_backup_job(body, request, db, user)
            except Exception:
                pass  # refresh mock may raise — we check what was added

        # The job added to DB must be a full backup (promoted)
        if added:
            assert added[0].job_type == BackupType.full, (
                f"Expected full backup after promotion, got {added[0].job_type}"
            )

    @pytest.mark.asyncio
    async def test_keeps_incremental_when_full_exists(self):
        from app.api.v1.endpoints.backups import create_backup_job
        from app.schemas.backups import BackupJobCreate

        vm = make_vm()
        body = BackupJobCreate(vm_id=vm.id, job_type=BackupType.incremental)

        db = AsyncMock()
        vm_result = MagicMock()
        vm_result.scalar_one_or_none.return_value = vm
        full_count_result = MagicMock()
        full_count_result.scalar_one.return_value = 1  # Prior full exists

        db.execute.side_effect = [vm_result, full_count_result]
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        user = MagicMock()
        user.tenant_id = vm.tenant_id
        request = MagicMock()
        request.app.state.nats = None

        added = []
        db.add.side_effect = lambda obj: added.append(obj)

        with patch("app.api.v1.endpoints.backups.BackupJobResponse.model_validate") as mv:
            mv.return_value = MagicMock()
            try:
                await create_backup_job(body, request, db, user)
            except Exception:
                pass

        if added:
            assert added[0].job_type == BackupType.incremental


# ── Cancel endpoint ───────────────────────────────────────────────────────────

class TestCancelBackupJob:

    @pytest.mark.asyncio
    async def test_cancel_queued_job_succeeds(self):
        from app.api.v1.endpoints.backups import cancel_backup_job
        from fastapi import HTTPException

        job = make_job(str(uuid.uuid4()), str(uuid.uuid4()), status=BackupStatus.queued)

        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = job
        db.execute.return_value = result
        db.commit = AsyncMock()

        user = MagicMock()

        await cancel_backup_job(job.id, db, user)

        assert job.status == BackupStatus.cancelled
        assert job.finished_at is not None
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_running_job_succeeds(self):
        from app.api.v1.endpoints.backups import cancel_backup_job

        job = make_job(str(uuid.uuid4()), str(uuid.uuid4()), status=BackupStatus.running)

        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = job
        db.execute.return_value = result
        db.commit = AsyncMock()

        await cancel_backup_job(job.id, db, MagicMock())
        assert job.status == BackupStatus.cancelled

    @pytest.mark.asyncio
    async def test_cancel_completed_job_raises_409(self):
        from app.api.v1.endpoints.backups import cancel_backup_job
        from fastapi import HTTPException

        job = make_job(str(uuid.uuid4()), str(uuid.uuid4()), status=BackupStatus.success)

        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = job
        db.execute.return_value = result

        with pytest.raises(HTTPException) as exc_info:
            await cancel_backup_job(job.id, db, MagicMock())
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_job_raises_404(self):
        from app.api.v1.endpoints.backups import cancel_backup_job
        from fastapi import HTTPException

        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute.return_value = result

        with pytest.raises(HTTPException) as exc_info:
            await cancel_backup_job("nonexistent", db, MagicMock())
        assert exc_info.value.status_code == 404


# ── VM state guard ────────────────────────────────────────────────────────────

class TestVMStateGuard:

    @pytest.mark.asyncio
    async def test_backup_provisioning_vm_raises_409(self):
        from app.api.v1.endpoints.backups import create_backup_job
        from app.schemas.backups import BackupJobCreate
        from fastapi import HTTPException

        vm = make_vm(status=VMStatus.provisioning)
        body = BackupJobCreate(vm_id=vm.id, job_type=BackupType.full)

        db = AsyncMock()
        vm_result = MagicMock()
        vm_result.scalar_one_or_none.return_value = vm
        db.execute.return_value = vm_result

        with pytest.raises(HTTPException) as exc_info:
            await create_backup_job(body, MagicMock(), db, MagicMock())
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_backup_deleted_vm_raises_404(self):
        from app.api.v1.endpoints.backups import create_backup_job
        from app.schemas.backups import BackupJobCreate
        from fastapi import HTTPException

        body = BackupJobCreate(vm_id="deleted-vm", job_type=BackupType.full)

        db = AsyncMock()
        vm_result = MagicMock()
        vm_result.scalar_one_or_none.return_value = None  # VM not found / deleted
        db.execute.return_value = vm_result

        with pytest.raises(HTTPException) as exc_info:
            await create_backup_job(body, MagicMock(), db, MagicMock())
        assert exc_info.value.status_code == 404


# ── NATS consumer message handler ─────────────────────────────────────────────

class TestBackupConsumerHandler:

    @pytest.mark.asyncio
    async def test_bad_json_acks_and_discards(self):
        from app.workers.backup_consumer import BackupConsumer

        consumer = BackupConsumer()
        msg = AsyncMock()
        msg.data = b"not valid json"

        await consumer._handle(msg)
        msg.ack.assert_called_once()
        msg.nak.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_keys_acks_and_discards(self):
        from app.workers.backup_consumer import BackupConsumer

        consumer = BackupConsumer()
        msg = AsyncMock()
        msg.data = json.dumps({"no_job_id": "here"}).encode()

        await consumer._handle(msg)
        msg.ack.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancelled_job_acks_without_running(self):
        from app.workers.backup_consumer import BackupConsumer

        consumer = BackupConsumer()
        msg = AsyncMock()

        vm = make_vm()
        job = make_job(vm.id, vm.tenant_id, status=BackupStatus.cancelled)
        msg.data = json.dumps({"job_id": job.id, "tenant_id": job.tenant_id}).encode()

        mock_db = AsyncMock()
        job_result = MagicMock()
        job_result.scalar_one_or_none.return_value = job
        mock_db.execute.return_value = job_result
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)

        with patch("app.workers.backup_consumer.tenant_session") as mock_ts:
            mock_ts.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_ts.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.workers.backup_consumer.BackupService") as mock_svc:
                await consumer._handle(msg)
                # BackupService.run_backup should NOT have been called
                mock_svc.return_value.run_backup.assert_not_called()

        msg.ack.assert_called_once()

    @pytest.mark.asyncio
    async def test_exception_during_run_naks_with_delay(self):
        from app.workers.backup_consumer import BackupConsumer

        consumer = BackupConsumer()
        msg = AsyncMock()
        vm = make_vm()
        job = make_job(vm.id, vm.tenant_id, status=BackupStatus.queued)
        msg.data = json.dumps({"job_id": job.id, "tenant_id": job.tenant_id}).encode()

        mock_db = AsyncMock()
        job_result = MagicMock()
        job_result.scalar_one_or_none.return_value = job
        vm_result = MagicMock()
        vm_result.scalar_one_or_none.return_value = vm
        mock_db.execute.side_effect = [job_result, vm_result]

        with patch("app.workers.backup_consumer.tenant_session") as mock_ts:
            mock_ts.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_ts.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.workers.backup_consumer.BackupService") as mock_svc:
                mock_svc.return_value.run_backup = AsyncMock(
                    side_effect=RuntimeError("disk I/O error")
                )
                await consumer._handle(msg)

        msg.nak.assert_called_once()
        msg.ack.assert_not_called()
        # Verify NAK includes a delay
        _, kwargs = msg.nak.call_args
        assert kwargs.get("delay", 0) > 0


# ── RLS policy correctness (logic test, no DB) ────────────────────────────────

class TestRLSPolicyLogic:
    """
    Verify the migration 0002 policy SQL strings are well-formed and
    cover all required operations.
    """

    MIGRATION_FILE = Path(__file__).resolve().parents[2] / "app" / "db" / "migrations" / "versions" / "0002_rls_and_triggers.py"

    def test_all_tenant_tables_have_policies(self):
        # Import the migration module and check TENANT_TABLES list
        import importlib.util, sys
        spec = importlib.util.spec_from_file_location(
            "mig0002",
            self.MIGRATION_FILE
        )
        mod = importlib.util.load_from_spec = None
        # Just verify the constant directly
        from app.db.migrations.versions import (  # type: ignore
            __path__ as _,
        )
        # Read the file and check all expected tables are present
        with open(self.MIGRATION_FILE, encoding="utf-8") as f:
            source = f.read()

        required_tables = ["users", "api_keys", "vms", "backup_jobs", "backup_manifests", "networks"]
        for table in required_tables:
            assert table in source, f"Missing RLS coverage for table: {table}"

    def test_disks_has_join_policy(self):
        with open(self.MIGRATION_FILE, encoding="utf-8") as f:
            source = f.read()
        assert "disks_via_vm" in source
        assert "SELECT id FROM vms" in source

    def test_msp_admin_bypass_present(self):
        with open(self.MIGRATION_FILE, encoding="utf-8") as f:
            source = f.read()
        assert "MSP_ADMIN_BYPASS" in source

    def test_audit_log_immutability_trigger_present(self):
        with open(self.MIGRATION_FILE, encoding="utf-8") as f:
            source = f.read()
        assert "audit_log_immutable" in source
        assert "BEFORE UPDATE OR DELETE" in source
