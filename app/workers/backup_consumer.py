"""
app/workers/backup_consumer.py
NATS JetStream consumer — pulls backup.job.queued, runs BackupService.run_backup().
Retry: max 3 deliveries, NAK with 30s delay on failure, dead-letter after 3rd.
"""
import asyncio, json
import structlog
from sqlalchemy import select
from app.core.config import get_settings
from app.db.session import tenant_session
from app.models import BackupJob, BackupStatus, VM
from app.services.backup_service import BackupService

log = structlog.get_logger(__name__)
settings = get_settings()

STREAM_NAME = "BACKUP_JOBS"
CONSUMER_NAME = "backup-worker"
SUBJECT = "backup.job.queued"
ACK_WAIT_SECONDS = 600
MAX_DELIVER = 3


class BackupConsumer:
    def __init__(self) -> None:
        self._nc = None
        self._js = None
        self._shutdown = asyncio.Event()

    async def connect(self) -> None:
        import nats
        from nats.js.api import ConsumerConfig, DeliverPolicy, AckPolicy
        self._nc = await nats.connect(settings.NATS_URL)
        self._js = self._nc.jetstream()
        try:
            await self._js.add_stream(name=STREAM_NAME, subjects=[SUBJECT])
        except Exception:
            pass  # already exists
        log.info("backup_consumer.connected", url=settings.NATS_URL)

    async def run(self) -> None:
        import nats
        from nats.js.api import ConsumerConfig, DeliverPolicy, AckPolicy
        await self.connect()
        sub = await self._js.pull_subscribe(
            SUBJECT, durable=CONSUMER_NAME,
            config=ConsumerConfig(
                ack_policy=AckPolicy.EXPLICIT,
                deliver_policy=DeliverPolicy.ALL,
                ack_wait=ACK_WAIT_SECONDS,
                max_deliver=MAX_DELIVER,
                max_ack_pending=1,
            ),
        )
        log.info("backup_consumer.listening", subject=SUBJECT)
        while not self._shutdown.is_set():
            try:
                msgs = await sub.fetch(batch=1, timeout=5.0)
            except Exception:
                await asyncio.sleep(1)
                continue
            for msg in msgs:
                await self._handle(msg)
        if self._nc:
            await self._nc.drain()

    async def _handle(self, msg) -> None:
        try:
            data = json.loads(msg.data.decode())
            job_id = data["job_id"]
            tenant_id = data["tenant_id"]
        except Exception as exc:
            log.error("backup_consumer.bad_message", error=str(exc))
            await msg.ack()
            return

        log.info("backup_consumer.processing", job_id=job_id)
        try:
            async with tenant_session(tenant_id) as db:
                job = (await db.execute(select(BackupJob).where(BackupJob.id == job_id))).scalar_one_or_none()
                if job is None or job.status == BackupStatus.cancelled:
                    await msg.ack()
                    return
                vm = (await db.execute(select(VM).where(VM.id == job.vm_id))).scalar_one_or_none()
                if vm is None:
                    await msg.ack()
                    return
                await BackupService(db).run_backup(job, vm)
            await msg.ack()
            log.info("backup_consumer.done", job_id=job_id, status=job.status.value)
        except Exception as exc:
            log.error("backup_consumer.error", job_id=job_id, error=str(exc))
            await msg.nak(delay=30)

    async def shutdown(self) -> None:
        self._shutdown.set()


async def _main() -> None:
    import signal
    consumer = BackupConsumer()
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(consumer.shutdown()))
    loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(consumer.shutdown()))
    await consumer.run()


if __name__ == "__main__":
    asyncio.run(_main())
