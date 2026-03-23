import type { AuditEvent } from '../../types'
import { AuditRow } from './AuditRow'

interface Props {
  events:    AuditEvent[]
  isLoading: boolean
}

export function AuditTable({ events, isLoading }: Props) {
  return (
    <div className="bg-white dark:bg-dark-surface border border-black/[0.07] dark:border-white/[0.07] rounded-xl overflow-hidden">
      <div className="grid grid-cols-[180px_160px_1fr_160px_40px] px-3 py-2 bg-slate-50 dark:bg-dark-bg3 border-b border-black/[0.05] dark:border-white/[0.05]">
        {['Timestamp', 'Action', 'Resource', 'User', ''].map(h => (
          <div key={h} className="text-[10px] font-semibold uppercase tracking-[0.8px] text-slate-500 dark:text-gray-400">{h}</div>
        ))}
      </div>

      {isLoading && <div className="px-3 py-6 text-[12px] text-slate-400 dark:text-gray-500">Loading audit events…</div>}
      {!isLoading && events.length === 0 && <div className="px-3 py-6 text-[12px] text-slate-400 dark:text-gray-500">No events found.</div>}

      {!isLoading && events.map(e => <AuditRow key={e.id} event={e} />)}
    </div>
  )
}
