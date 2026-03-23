import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { Badge } from '../ui/Badge'
import type { AuditEvent } from '../../types'
import { formatDateTime } from '../../utils/format'

function actionBadge(action: string): 'blue' | 'teal' | 'purple' | 'warning' | 'danger' {
  if (action.startsWith('vm.')) return 'blue'
  if (action.startsWith('backup.')) return 'teal'
  if (action.startsWith('tenant.')) return 'purple'
  if (action.startsWith('auth.')) return 'warning'
  if (action.includes('error') || action.includes('failed')) return 'danger'
  return 'blue'
}

export function AuditRow({ event }: { event: AuditEvent }) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <div className="grid grid-cols-[180px_160px_1fr_160px_40px] items-center px-3 py-2.5 border-b border-black/[0.05] dark:border-white/[0.04] hover:bg-slate-50 dark:hover:bg-dark-bg3 transition-colors">
        <div className="text-[11px] text-slate-500 dark:text-gray-400 font-mono">
          {formatDateTime(event.ts)}
        </div>
        <div>
          <Badge variant={actionBadge(event.action)}>{event.action}</Badge>
        </div>
        <div className="text-[12px] text-slate-700 dark:text-gray-300 truncate">
          {event.resource_type} {event.resource_id ?? '—'}
        </div>
        <div className="text-[11px] text-slate-500 dark:text-gray-400 font-mono truncate">
          {event.user_id ?? 'system'}
        </div>
        <button
          onClick={() => setOpen(v => !v)}
          className="text-slate-400 dark:text-gray-500 hover:text-slate-700 dark:hover:text-gray-300"
        >
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>

      {open && (
        <div className="px-4 py-3 border-b border-black/[0.05] dark:border-white/[0.04] bg-slate-50 dark:bg-dark-bg3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
            <Field label="Action" value={event.action} />
            <Field label="Resource Type" value={event.resource_type} />
            <Field label="Resource ID" value={event.resource_id ?? '—'} />
            <Field label="Tenant ID" value={event.tenant_id ?? '—'} />
            <Field label="User ID" value={event.user_id ?? '—'} />
            <Field label="IP Address" value={event.ip_address ?? '—'} />
            <Field label="User Agent" value={event.user_agent ?? '—'} />
            <Field label="Integrity Hash" value={event.integrity_hash} mono />
          </div>
        </div>
      )}
    </>
  )
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex justify-between gap-3 border border-black/[0.06] dark:border-white/[0.06] rounded-md px-2 py-1.5 bg-white dark:bg-dark-surface">
      <span className="text-slate-500 dark:text-gray-400">{label}</span>
      <span className={`text-slate-700 dark:text-gray-300 truncate ${mono ? 'font-mono' : ''}`} title={value}>{value}</span>
    </div>
  )
}
