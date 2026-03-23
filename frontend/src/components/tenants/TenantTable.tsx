import type { TenantResponse } from '../../types'
import { TenantRow } from './TenantRow'

interface Props {
  tenants:      TenantResponse[]
  isLoading:    boolean
  onSuspend:    (id: string, name: string) => void
  onReinstate:  (id: string) => void
}

export function TenantTable({ tenants, isLoading, onSuspend, onReinstate }: Props) {
  return (
    <div className="bg-white dark:bg-dark-surface border border-black/[0.07] dark:border-white/[0.07] rounded-xl overflow-hidden">
      <div className="grid grid-cols-[1.5fr_110px_110px_90px_90px_110px_170px_40px] px-3 py-2 bg-slate-50 dark:bg-dark-bg3 border-b border-black/[0.05] dark:border-white/[0.05]">
        {['Tenant', 'Plan', 'Status', 'VMs', 'Users', 'Storage', 'Actions', ''].map(h => (
          <div key={h} className="text-[10px] font-semibold uppercase tracking-[0.8px] text-slate-500 dark:text-gray-400">{h}</div>
        ))}
      </div>

      {isLoading && <div className="px-3 py-6 text-[12px] text-slate-400 dark:text-gray-500">Loading tenants…</div>}
      {!isLoading && tenants.length === 0 && <div className="px-3 py-6 text-[12px] text-slate-400 dark:text-gray-500">No tenants found.</div>}

      {!isLoading && tenants.map(t => (
        <TenantRow
          key={t.id}
          tenant={t}
          onSuspend={onSuspend}
          onReinstate={onReinstate}
        />
      ))}
    </div>
  )
}
