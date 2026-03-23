import { CheckCircle2, Loader2, XCircle, RotateCw, FileText } from 'lucide-react'
import type { BackupJobResponse, VMResponse } from '../../types'
import { formatBytes, formatRelativeTime, formatDuration, dedupSavings } from '../../utils/format'
import { BackupProgress } from './BackupProgress'
import { Button } from '../ui/Button'

interface Props {
  job: BackupJobResponse
  vm?: VMResponse
  onRetry?: (job: BackupJobResponse) => void
  onManifest?: (job: BackupJobResponse) => void
}

function iconFor(status: BackupJobResponse['status']) {
  if (status === 'running' || status === 'queued') return <Loader2 size={14} className="animate-spin text-accent" />
  if (status === 'success') return <CheckCircle2 size={14} className="text-success" />
  if (status === 'failed' || status === 'cancelled') return <XCircle size={14} className="text-nova-danger" />
  return <FileText size={14} className="text-slate-400" />
}

export function BackupJobRow({ job, vm, onRetry, onManifest }: Props) {
  const isRunning  = job.status === 'running' || job.status === 'queued'
  const isDone     = job.status === 'success'
  const isFailed   = job.status === 'failed' || job.status === 'cancelled'

  const ratio = job.bytes_written > 0 ? job.bytes_read / job.bytes_written : 0
  const ratioLabel = ratio > 0 ? `${ratio.toFixed(2)}x` : '—'

  const durationSec = job.started_at && job.finished_at
    ? Math.max(0, Math.round((new Date(job.finished_at).getTime() - new Date(job.started_at).getTime()) / 1000))
    : null

  const progress = job.bytes_read > 0
    ? Math.min(99, Math.round((job.bytes_written / job.bytes_read) * 100))
    : job.status === 'running'
    ? 10
    : 0

  return (
    <div className="border-b border-black/[0.05] dark:border-white/[0.05] px-4 py-3 last:border-b-0">
      <div className="flex items-start gap-3">
        <div className="mt-0.5">{iconFor(job.status)}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-3">
            <div className="text-[12px] font-medium text-slate-900 dark:text-gray-100 truncate">
              {vm?.name ?? job.vm_id}
            </div>
            <div className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-dark-bg3 text-slate-500 dark:text-gray-400">
              {job.job_type}
            </div>
          </div>

          <div className="text-[11px] text-slate-500 dark:text-gray-400 mt-0.5">
            {isRunning && `Running · ${formatBytes(job.bytes_read)} read · ${formatBytes(job.bytes_written)} written`}
            {isDone && `Completed ${job.finished_at ? formatRelativeTime(job.finished_at) : ''}`}
            {isFailed && (job.error_message ? `Failed · ${job.error_message}` : 'Failed')}
          </div>

          {isRunning && <BackupProgress value={progress} />}

          {(isDone || isFailed) && (
            <div className="mt-2 grid grid-cols-2 gap-2 text-[10px] text-slate-500 dark:text-gray-400">
              <div className="flex justify-between"><span>Duration</span><span className="font-mono">{durationSec != null ? formatDuration(durationSec) : '—'}</span></div>
              <div className="flex justify-between"><span>Dedup ratio</span><span className="font-mono">{ratioLabel}</span></div>
              <div className="flex justify-between"><span>Savings</span><span className="font-mono">{ratio > 0 ? dedupSavings(ratio) : '—'}</span></div>
              <div className="flex justify-between"><span>Written</span><span className="font-mono">{formatBytes(job.bytes_written)}</span></div>
            </div>
          )}
        </div>
      </div>

      <div className="flex gap-2 mt-2">
        {isDone && (
          <Button size="sm" onClick={() => onManifest?.(job)} iconLeft={<FileText size={12} />}>
            Manifest
          </Button>
        )}
        {isFailed && (
          <Button size="sm" variant="secondary" onClick={() => onRetry?.(job)} iconLeft={<RotateCw size={12} />}>
            Retry
          </Button>
        )}
      </div>
    </div>
  )
}
