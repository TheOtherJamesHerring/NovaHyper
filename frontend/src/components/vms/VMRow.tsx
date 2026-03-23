import { clsx } from 'clsx'
import { MoreHorizontal, Play, Square, RefreshCw, Pause } from 'lucide-react'
import { useState } from 'react'
import type { CSSProperties } from 'react'
import type { VMMetrics, VMResponse } from '../../types'
import { Popover } from '../ui/Popover'
import { OsIcon } from './OsIcons'
import { formatRelativeTime, formatMB, formatDate } from '../../utils/format'
import { getVMMetrics } from '../../api/vms'

/* ── Status pill ── */
const STATUS_CLASSES: Record<string, string> = {
  running:      'bg-[rgba(56,217,169,0.12)] text-success',
  stopped:      'bg-[rgba(107,114,128,0.12)] text-slate-500 dark:text-gray-400',
  paused:       'bg-[rgba(245,158,11,0.12)] text-nova-warn',
  error:        'bg-[rgba(239,68,68,0.12)] text-nova-danger',
  provisioning: 'bg-[rgba(79,142,247,0.12)] text-accent',
  deleted:      'bg-[rgba(107,114,128,0.12)] text-slate-400',
}

function StatusPill({ vm }: { vm: VMResponse }) {
  const label = vm.status.charAt(0).toUpperCase() + vm.status.slice(1)

  const popContent = (
    <div className="p-3 min-w-[180px]">
      <div className="text-[11px] text-slate-500 dark:text-gray-400 mb-1">Current state</div>
      <div className={clsx('text-[13px] font-medium', STATUS_CLASSES[vm.status])}>{label}</div>
      <div className="mt-2 text-[11px] text-slate-500 dark:text-gray-400">Last updated</div>
      <div className="text-[12px] text-slate-700 dark:text-gray-300">{formatRelativeTime(vm.updated_at)}</div>
    </div>
  )

  return (
    <Popover trigger={
      <span className={clsx('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium cursor-default', STATUS_CLASSES[vm.status])}>
        <span className="w-1.5 h-1.5 rounded-full bg-current" />
        {label}
      </span>
    } content={popContent} />
  )
}

/* ── CPU bar ── */
function CpuBar({ pct, vm }: { pct: number; vm: VMResponse }) {
  const [metrics, setMetrics] = useState<VMMetrics | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const effectivePct = metrics?.cpu_percent ?? pct
  const color = effectivePct >= 90 ? 'bg-nova-danger' : effectivePct >= 75 ? 'bg-nova-warn' : 'bg-accent'

  const loadMetrics = async () => {
    if (loading || metrics || vm.status !== 'running') return
    setLoading(true)
    setError(null)
    try {
      const m = await getVMMetrics(vm.id)
      setMetrics(m)
    } catch {
      setError('Unavailable')
    } finally {
      setLoading(false)
    }
  }

  const popContent = (
    <div className="p-3 min-w-[180px]">
      <div className="text-[11px] text-slate-500 dark:text-gray-400 mb-1">CPU usage</div>
      <div className="font-mono text-[22px] font-medium text-accent leading-none mb-2">
        {loading ? '...' : `${effectivePct}%`}
      </div>
      <div className="flex flex-col gap-1 text-[11px]">
        <div className="flex justify-between">
          <span className="text-slate-500 dark:text-gray-400">5-min avg</span>
          <span className="font-mono text-slate-700 dark:text-gray-300">
            {metrics ? `${metrics.cpu_5min_avg}%` : '—'}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500 dark:text-gray-400">15-min avg</span>
          <span className="font-mono text-slate-700 dark:text-gray-300">
            {metrics ? `${metrics.cpu_15min_avg}%` : '—'}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500 dark:text-gray-400">RAM</span>
          <span className="font-mono text-slate-700 dark:text-gray-300">
            {metrics ? `${formatMB(metrics.mem_used_mb)} / ${formatMB(metrics.mem_total_mb)}` : formatMB(vm.ram_mb)}
          </span>
        </div>
        {error && <div className="text-[10px] text-nova-danger">metrics: {error}</div>}
      </div>
    </div>
  )

  return (
    <Popover trigger={
      <div className="flex items-center gap-2 cursor-default">
        <div className="w-14 h-1 rounded-full bg-slate-200 dark:bg-dark-bg3 overflow-hidden">
          <div className={clsx('h-full rounded-full transition-[width]', color)} style={{ width: `${effectivePct}%` }} />
        </div>
        <span className="font-mono text-[11px] text-slate-500 dark:text-gray-400">{effectivePct}%</span>
      </div>
    } content={popContent} onOpenChange={open => { if (open) void loadMetrics() }} />
  )
}

/* ── Last backup cell ── */
function BackupCell({ vm }: { vm: VMResponse }) {
  const text = vm.disks.some(d => d.bitmap_name)
    ? 'Enabled'
    : 'Never'

  const popContent = (
    <div className="p-3 min-w-[200px]">
      <div className="text-[11px] text-slate-500 dark:text-gray-400 mb-1">Backup info</div>
      <div className="flex flex-col gap-1 text-[11px]">
        <div className="flex justify-between">
          <span className="text-slate-500 dark:text-gray-400">Disks with bitmap</span>
          <span className="font-mono text-slate-700 dark:text-gray-300">
            {vm.disks.filter(d => d.bitmap_name).length}/{vm.disks.length}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500 dark:text-gray-400">Policy</span>
          <span className="font-mono text-slate-700 dark:text-gray-300 truncate max-w-[100px]">
            {Object.keys(vm.backup_policy).length > 0 ? 'Configured' : 'None'}
          </span>
        </div>
      </div>
    </div>
  )

  return (
    <Popover trigger={
      <span className="cursor-default text-[12px] text-slate-500 dark:text-gray-400">{text}</span>
    } content={popContent} />
  )
}

/* ── Name + OS popover ── */
function NameCell({ vm }: { vm: VMResponse }) {
  const popContent = (
    <div className="p-3 min-w-[220px]">
      <div className="font-medium text-[13px] text-slate-900 dark:text-gray-100 mb-2">{vm.name}</div>
      <div className="flex flex-col gap-1 text-[11px]">
        {[
          ['OS type',   vm.os_type],
          ['OS variant', vm.os_variant ?? '—'],
          ['Host',      vm.host_id ?? '—'],
          ['UUID',      vm.libvirt_uuid ?? '—'],
          ['Created',   formatDate(vm.created_at)],
          ['vCPU',      String(vm.vcpus)],
          ['RAM',       formatMB(vm.ram_mb)],
        ].map(([k, v]) => (
          <div key={k} className="flex justify-between gap-3">
            <span className="text-slate-500 dark:text-gray-400">{k}</span>
            <span className="font-mono text-slate-700 dark:text-gray-300 truncate max-w-[130px]" title={v}>{v}</span>
          </div>
        ))}
      </div>
    </div>
  )

  return (
    <Popover trigger={
      <div className="flex items-center gap-2 cursor-default">
        <div className="w-6 h-6 rounded bg-slate-100 dark:bg-dark-bg3 border border-black/[0.07] dark:border-white/[0.07] flex items-center justify-center shrink-0">
          <OsIcon osType={vm.os_type} osVariant={vm.os_variant} size={16} />
        </div>
        <span className="font-medium text-slate-900 dark:text-gray-100 hover:text-accent transition-colors">
          {vm.name}
        </span>
      </div>
    } content={popContent} />
  )
}

/* ── Actions menu ── */
function ActionsMenu({ vm, onAction }: { vm: VMResponse; onAction: (action: string, vm: VMResponse) => void }) {
  const [open, setOpen] = useState(false)

  const actions = [
    { label: 'Start',   icon: <Play    size={12} />, action: 'start',  show: vm.status === 'stopped'  },
    { label: 'Stop',    icon: <Square  size={12} />, action: 'stop',   show: vm.status === 'running'  },
    { label: 'Pause',   icon: <Pause   size={12} />, action: 'pause',  show: vm.status === 'running'  },
    { label: 'Reboot',  icon: <RefreshCw size={12}/>, action: 'reboot', show: vm.status === 'running' },
  ].filter(a => a.show)

  return (
    <div className="relative">
      <button
        onClick={e => { e.stopPropagation(); setOpen(v => !v) }}
        className="p-1 rounded text-slate-400 dark:text-gray-500 hover:text-slate-700 dark:hover:text-gray-200 hover:bg-slate-100 dark:hover:bg-dark-bg3 transition-colors"
      >
        <MoreHorizontal size={14} />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-0.5 z-50 w-36 bg-white dark:bg-dark-bg2 border border-black/[0.08] dark:border-white/[0.1] rounded-lg shadow-xl overflow-hidden text-[12px]">
            {actions.map(a => (
              <button
                key={a.action}
                onClick={e => { e.stopPropagation(); setOpen(false); onAction(a.action, vm) }}
                className="flex items-center gap-2 w-full px-3 py-2 text-slate-700 dark:text-gray-300 hover:bg-slate-50 dark:hover:bg-dark-bg3 transition-colors"
              >
                {a.icon} {a.label}
              </button>
            ))}
            {actions.length === 0 && (
              <div className="px-3 py-2 text-slate-400 dark:text-gray-500">No actions</div>
            )}
          </div>
        </>
      )}
    </div>
  )
}

/* ── Main row ── */
interface VMRowProps {
  vm:       VMResponse
  style?:   CSSProperties
  selected: boolean
  onSelect: (id: string, val: boolean) => void
  onAction: (action: string, vm: VMResponse) => void
}

export function VMRow({ vm, style, selected, onSelect, onAction }: VMRowProps) {
  const totalDisk = vm.disks.reduce((s, d) => s + d.size_gb, 0)

  return (
    <div
      style={style}
      className={clsx(
        'grid grid-cols-[36px_2fr_1fr_56px_72px_80px_80px_100px_44px] items-center gap-0',
        'border-b border-black/[0.05] dark:border-white/[0.04]',
        'hover:bg-slate-50 dark:hover:bg-dark-bg3 transition-colors',
        selected && 'bg-accent/[0.06]'
      )}
    >
      <div className="px-3 flex items-center">
        <input
          type="checkbox"
          checked={selected}
          onChange={e => onSelect(vm.id, e.target.checked)}
          className="accent-accent w-3.5 h-3.5"
          onClick={e => e.stopPropagation()}
        />
      </div>
      <div className="px-2 py-2.5 truncate"><NameCell vm={vm} /></div>
      <div className="px-2 py-2.5"><StatusPill vm={vm} /></div>
      <div className="px-2 py-2.5 font-mono text-[11px] text-slate-500 dark:text-gray-400">{vm.vcpus}</div>
      <div className="px-2 py-2.5 font-mono text-[11px] text-slate-500 dark:text-gray-400">{formatMB(vm.ram_mb)}</div>
      <div className="px-2 py-2.5"><CpuBar pct={vm.status === 'running' ? Math.floor(Math.random() * 80) : 0} vm={vm} /></div>
      <div className="px-2 py-2.5 font-mono text-[11px] text-slate-500 dark:text-gray-400">{totalDisk} GB</div>
      <div className="px-2 py-2.5"><BackupCell vm={vm} /></div>
      <div className="px-2 py-2.5 flex justify-end"><ActionsMenu vm={vm} onAction={onAction} /></div>
    </div>
  )
}
