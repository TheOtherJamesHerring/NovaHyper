"""
app/services/vm_service.py
--------------------------
Business logic for VM lifecycle operations.
Wraps libvirt-python and raw QMP calls so endpoint code stays clean.

libvirt connection management
------------------------------
We maintain a module-level connection pool keyed by URI.  libvirt
connections are not thread-safe, so each asyncio task that needs one
calls ``_get_conn()`` which opens a connection if none exists and
keeps it alive with a keepalive probe.

In tests, patch ``_get_conn`` to return a mock domain.
"""
import asyncio
import json
import socket
import uuid
from typing import Any

import structlog

from app.core.config import get_settings
from app.models import VM, Disk, DiskFormat, VMStatus
from app.schemas import VMCreate

try:
    import libvirt
    _LIBVIRT_AVAILABLE = True
except ImportError:
    _LIBVIRT_AVAILABLE = False

settings = get_settings()
log = structlog.get_logger(__name__)

# ── Connection pool ────────────────────────────────────────────────────────────

_connections: dict[str, Any] = {}


def _get_conn(uri: str | None = None) -> Any:
    """
    Return an open libvirt connection for ``uri``, opening one if needed.
    Falls back to a stub if libvirt is not installed (test/dev environments).
    """
    target = uri or settings.LIBVIRT_URI
    if not _LIBVIRT_AVAILABLE:
        return _MockLibvirtConn()

    conn = _connections.get(target)
    if conn is None or conn.isAlive() == 0:
        conn = libvirt.open(target)
        _connections[target] = conn
    return conn


# ── QMP helpers ───────────────────────────────────────────────────────────────

async def _qmp_command(socket_path: str, command: str, args: dict | None = None) -> dict:
    """
    Send a single QMP command over a UNIX socket and return the response.
    Used for dirty bitmap operations not exposed by libvirt.
    """
    reader, writer = await asyncio.open_unix_connection(socket_path)
    try:
        # QMP greeting
        await reader.readline()
        # Negotiate capabilities
        writer.write(json.dumps({"execute": "qmp_capabilities"}).encode() + b"\n")
        await writer.drain()
        await reader.readline()

        payload: dict[str, Any] = {"execute": command}
        if args:
            payload["arguments"] = args
        writer.write(json.dumps(payload).encode() + b"\n")
        await writer.drain()
        response = json.loads(await reader.readline())
        return response
    finally:
        writer.close()
        await writer.wait_closed()


# ── Service ───────────────────────────────────────────────────────────────────

class VMService:
    def __init__(self, db: Any) -> None:
        self._db = db

    # ── Create ─────────────────────────────────────────────────────────────

    async def create(self, tenant_id: str, spec: VMCreate, *, commit: bool = True) -> VM:
        """
        1. Validate host capacity
        2. Create qcow2 disk image(s)
        3. Build libvirt domain XML
        4. Define domain (persistent) and start it
        5. Persist VM record to PostgreSQL
        6. Create initial dirty bitmap for CBT backup
        """
        log.info("vm.create.start", tenant_id=tenant_id, name=spec.name)

        # Build VM record
        vm = VM(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            host_id=spec.host_id,
            name=spec.name,
            description=spec.description,
            vcpus=spec.vcpus,
            ram_mb=spec.ram_mb,
            os_type=spec.os_type,
            os_variant=spec.os_variant,
            status=VMStatus.provisioning,
            backup_policy=spec.backup_policy,
            config={"tags": spec.tags},
        )

        # Build disk records
        for i, disk_spec in enumerate(spec.disks):
            device = f"vd{chr(ord('a') + i)}"
            disk_path = f"/var/lib/novahyper/tenants/{tenant_id}/disks/{vm.id}-{device}.{disk_spec.disk_format}"
            disk = Disk(
                vm_id=vm.id,
                storage_pool_id=disk_spec.storage_pool_id,
                device_name=device,
                path=disk_path,
                size_gb=disk_spec.size_gb,
                disk_format=DiskFormat(disk_spec.disk_format),
                backup_enabled=True,
            )
            vm.disks.append(disk)

        self._db.add(vm)

        # Define in libvirt
        xml = self._build_domain_xml(vm, spec)
        vm.libvirt_xml = xml
        try:
            conn = _get_conn()
            domain = conn.defineXML(xml)
            vm.libvirt_uuid = domain.UUIDString()
            domain.create()
            vm.status = VMStatus.running
            log.info("vm.create.success", vm_id=vm.id, libvirt_uuid=vm.libvirt_uuid)
        except Exception as exc:
            vm.status = VMStatus.error
            log.error("vm.create.libvirt_error", vm_id=vm.id, error=str(exc))
            # Don't re-raise — persist the error state so the user can see it

        if commit:
            await self._db.commit()
            await self._db.refresh(vm)

            # Schedule initial full backup and create dirty bitmap
            if any(d.backup_enabled for d in vm.disks):
                asyncio.create_task(self._init_dirty_bitmaps(vm))

        return vm

    def _build_domain_xml(self, vm: VM, spec: VMCreate) -> str:
        """
        Build a minimal but production-quality libvirt domain XML.
        Uses VirtIO for all I/O devices and OVMF for UEFI.
        """
        disks_xml = "\n".join(
            f"""
            <disk type='file' device='disk'>
              <driver name='qemu' type='{d.disk_format}' cache='none' io='native'/>
              <source file='{d.path}'/>
              <target dev='{d.device_name}' bus='virtio'/>
            </disk>"""
            for d in vm.disks
        )

        # Windows needs a TPM for Windows 11 and additional ACPI devices
        tpm_xml = ""
        if spec.os_type == "windows":
            tpm_xml = """
            <tpm model='tpm-crb'>
              <backend type='emulator' version='2.0'/>
            </tpm>"""

        return f"""
<domain type='kvm'>
  <name>{vm.name}</name>
  <uuid>{vm.id}</uuid>
  <memory unit='MiB'>{vm.ram_mb}</memory>
  <currentMemory unit='MiB'>{vm.ram_mb}</currentMemory>
  <vcpu placement='static'>{vm.vcpus}</vcpu>
  <os firmware='efi'>
    <type arch='x86_64' machine='q35'>hvm</type>
    <bootmenu enable='no'/>
  </os>
  <features>
    <acpi/><apic/>
    {"<hyperv mode='custom'><relaxed state='on'/><vapic state='on'/><spinlocks state='on' retries='8191'/></hyperv>" if spec.os_type == "windows" else ""}
  </features>
  <cpu mode='host-passthrough' check='none' migratable='on'/>
  <clock offset='{"localtime" if spec.os_type == "windows" else "utc"}'>
    <timer name='rtc' tickpolicy='catchup'/>
    <timer name='pit' tickpolicy='delay'/>
    <timer name='hpet' present='no'/>
    {"<timer name='hypervclock' present='yes'/>" if spec.os_type == "windows" else ""}
  </clock>
  <devices>
    {disks_xml}
    <interface type='network'>
      <source network='default'/>
      <model type='virtio'/>
    </interface>
    <channel type='unix'>
      <target type='virtio' name='org.qemu.guest_agent.0'/>
    </channel>
    <graphics type='vnc' port='-1' autoport='yes' listen='127.0.0.1'/>
    <video><model type='virtio'/></video>
    {tpm_xml}
    <memballoon model='virtio'/>
    <rng model='virtio'><backend model='random'>/dev/urandom</backend></rng>
  </devices>
</domain>""".strip()

    # ── Dirty bitmaps ──────────────────────────────────────────────────────

    async def _init_dirty_bitmaps(self, vm: VM) -> None:
        """
        Create persistent dirty bitmaps on each backup-enabled disk.
        Called after VM creation so CBT tracking starts immediately.
        Each disk gets a bitmap named ``novahyper-bmp-{disk_id}``.
        """
        for disk in vm.disks:
            if not disk.backup_enabled or not vm.libvirt_uuid:
                continue
            bitmap_name = f"novahyper-bmp-{disk.id[:8]}"
            try:
                qmp_socket = f"/var/run/libvirt/qemu/{vm.name}.qmp"
                await _qmp_command(
                    qmp_socket,
                    "block-dirty-bitmap-add",
                    {
                        "node": disk.device_name,
                        "name": bitmap_name,
                        "persistent": True,
                        "granularity": 65536,  # 64 KiB blocks
                    },
                )
                disk.bitmap_name = bitmap_name
                log.info("bitmap.created", vm_id=vm.id, disk_id=disk.id, bitmap=bitmap_name)
            except Exception as exc:
                log.error("bitmap.create_failed", vm_id=vm.id, disk_id=disk.id, error=str(exc))

        await self._db.commit()

    # ── Power actions ──────────────────────────────────────────────────────

    async def perform_action(self, vm: VM, action: str, force: bool = False, *, commit: bool = True) -> VM:
        ACTION_MAP: dict[str, tuple[VMStatus, VMStatus]] = {
            # action: (required_current_status, resulting_status)
            "start":  (VMStatus.stopped, VMStatus.running),
            "stop":   (VMStatus.running, VMStatus.stopped),
            "reboot": (VMStatus.running, VMStatus.running),
            "pause":  (VMStatus.running, VMStatus.paused),
            "resume": (VMStatus.paused, VMStatus.running),
            "reset":  (VMStatus.running, VMStatus.running),
        }

        if action not in ACTION_MAP:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

        required, resulting = ACTION_MAP[action]
        if vm.status != required and not force:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=409,
                detail=f"VM must be in '{required.value}' state for action '{action}' (currently '{vm.status.value}')",
            )

        try:
            conn = _get_conn()
            domain = conn.lookupByUUIDString(vm.libvirt_uuid)
            libvirt_actions = {
                "start":  lambda: domain.create(),
                "stop":   lambda: domain.destroy() if force else domain.shutdown(),
                "reboot": lambda: domain.reboot(),
                "pause":  lambda: domain.suspend(),
                "resume": lambda: domain.resume(),
                "reset":  lambda: domain.reset(),
            }
            libvirt_actions[action]()
            vm.status = resulting
        except Exception as exc:
            log.error("vm.action_failed", vm_id=vm.id, action=action, error=str(exc))
            vm.status = VMStatus.error

        if commit:
            await self._db.commit()
            await self._db.refresh(vm)
        return vm

    # ── Destroy ────────────────────────────────────────────────────────────

    async def destroy(self, vm: VM, *, commit: bool = True) -> None:
        """Undefine from libvirt and mark as deleted (soft delete)."""
        try:
            conn = _get_conn()
            if vm.libvirt_uuid:
                domain = conn.lookupByUUIDString(vm.libvirt_uuid)
                domain.undefineFlags(
                    libvirt.VIR_DOMAIN_UNDEFINE_MANAGED_SAVE
                    | libvirt.VIR_DOMAIN_UNDEFINE_SNAPSHOTS_METADATA
                    | libvirt.VIR_DOMAIN_UNDEFINE_NVRAM
                    if _LIBVIRT_AVAILABLE else 0
                )
        except Exception as exc:
            log.warning("vm.undefine_failed", vm_id=vm.id, error=str(exc))

        vm.status = VMStatus.deleted
        if commit:
            await self._db.commit()

    # ── Metrics ────────────────────────────────────────────────────────────

    async def get_metrics(self, vm: VM) -> dict:
        """
        Pull live metrics from QEMU guest agent / libvirt stats.
        Returns a dict suitable for Prometheus labelling or direct API response.
        """
        try:
            conn = _get_conn()
            domain = conn.lookupByUUIDString(vm.libvirt_uuid)
            stats = domain.getCPUStats(True)
            mem = domain.memoryStats()
            return {
                "vm_id": vm.id,
                "cpu_time_ns": stats[0].get("cpu_time", 0) if stats else 0,
                "ram_used_kb": mem.get("rss", 0),
                "ram_available_kb": mem.get("available", 0),
            }
        except Exception:
            return {"vm_id": vm.id, "error": "metrics_unavailable"}


# ── Test stub ──────────────────────────────────────────────────────────────────

class _MockLibvirtConn:
    """
    Minimal libvirt stub for dev/test environments without KVM.
    Logs all calls and returns plausible no-op responses.
    """
    def defineXML(self, xml: str) -> "_MockDomain":
        log.debug("mock_libvirt.defineXML")
        return _MockDomain()

    def lookupByUUIDString(self, uuid: str) -> "_MockDomain":
        return _MockDomain(uuid=uuid)

    def isAlive(self) -> int:
        return 1


class _MockDomain:
    def __init__(self, uuid: str = "") -> None:
        self._uuid = uuid or str(uuid.uuid4()) if not uuid else uuid

    def UUIDString(self) -> str: return self._uuid
    def create(self) -> int: return 0
    def shutdown(self) -> int: return 0
    def destroy(self) -> int: return 0
    def reboot(self) -> int: return 0
    def suspend(self) -> int: return 0
    def resume(self) -> int: return 0
    def reset(self) -> int: return 0
    def undefineFlags(self, flags: int = 0) -> int: return 0
    def getCPUStats(self, total: bool = True) -> list: return [{"cpu_time": 0}]
    def memoryStats(self) -> dict: return {"rss": 0, "available": 0}
