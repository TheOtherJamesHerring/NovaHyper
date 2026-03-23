import { useMemo } from 'react'
import { Download, RefreshCw } from 'lucide-react'
import { useBackups, useCreateBackup } from '../../hooks/useBackups'
import { useVMs } from '../../hooks/useVMs'
import { getBackupManifest } from '../../api/backups'
import { BackupJobRow } from './BackupJobRow'
import { Button } from '../ui/Button'

export function BackupPanel() {
  const backupsQ = useBackups({ page: 1, page_size: 50 })
  const runningQ = useBackups({ status: 'running', page: 1, page_size: 20 })
  const vmsQ     = useVMs({ page: 1, page_size: 100 })
  const createM  = useCreateBackup()

  const jobs  = backupsQ.data?.items ?? []
  const vms   = vmsQ.data?.items ?? []
  const vmMap = useMemo(() => new Map(vms.map(v => [v.id, v])), [vms])

  const runningCount = runningQ.data?.items.length ?? 0

  const triggerRetry = async (jobId: string) => {
    const original = jobs.find(j => j.id === jobId)
    if (!original) return
    await createM.mutateAsync({ vm_id: original.vm_id, job_type: original.job_type })
  }

  const openManifest = async (jobId: string) => {
    const manifest = await getBackupManifest(jobId)
    const text = JSON.stringify(manifest, null, 2)
    const blob = new Blob([text], { type: 'application/json' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url
    a.download = `backup-manifest-${jobId}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="bg-white dark:bg-dark-surface border border-black/[0.07] dark:border-white/[0.07] rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-black/[0.06] dark:border-white/[0.07] flex items-center gap-2">
        <h2 className="font-display text-[14px] font-semibold text-slate-900 dark:text-gray-100">Backup Jobs</h2>
        <span className="font-mono text-[10px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-dark-bg3 text-slate-500 dark:text-gray-400">
          {runningCount} running
        </span>
        <div className="ml-auto flex gap-2">
          <Button size="sm" onClick={() => backupsQ.refetch()} iconLeft={<RefreshCw size={12} />}>Refresh</Button>
          <Button
            size="sm"
            variant="primary"
            onClick={() => {
              const firstVm = vms[0]
              if (firstVm) createM.mutate({ vm_id: firstVm.id, job_type: 'incremental' })
            }}
            iconLeft={<Download size={12} />}
          >
            Trigger backup
          </Button>
        </div>
      </div>

      <div className="max-h-[420px] overflow-y-auto">
        {backupsQ.isLoading && <div className="px-4 py-6 text-[12px] text-slate-400 dark:text-gray-500">Loading backups…</div>}
        {!backupsQ.isLoading && jobs.length === 0 && (
          <div className="px-4 py-6 text-[12px] text-slate-400 dark:text-gray-500">No backup jobs yet.</div>
        )}
        {jobs.map(job => (
          <BackupJobRow
            key={job.id}
            job={job}
            vm={vmMap.get(job.vm_id)}
            onRetry={() => triggerRetry(job.id)}
            onManifest={() => openManifest(job.id)}
          />
        ))}
      </div>
    </div>
  )
}
