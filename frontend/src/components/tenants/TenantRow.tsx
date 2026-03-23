import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import type { TenantResponse } from '../../types'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { getTenantDetail, listTenantUsers } from '../../api/tenants'
import { listAudit } from '../../api/audit'

interface Props {
  tenant:      TenantResponse
  onSuspend:   (id: string, name: string) => void
  onReinstate: (id: string) => void
}

export function TenantRow({ tenant, onSuspend, onReinstate }: Props) {
  const [open, setOpen] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [detail, setDetail] = useState<TenantResponse | null>(null)
  const [users, setUsers] = useState<{ email: string; role: string }[] | null>(null)
  const [audits, setAudits] = useState<string[] | null>(null)

  const loadExpandedData = async () => {
    if (loadingDetail || detail) return
    setLoadingDetail(true)
    try {
      const [d, u, a] = await Promise.all([
        getTenantDetail(tenant.id),
        listTenantUsers(tenant.id),
        listAudit({ tenant_id: tenant.id, page: 1, page_size: 3 }),
      ])
      setDetail(d)
      setUsers(
        u === null
          ? null
          : u.map(user => ({
              email: user.email,
              role: user.role,
            }))
      )
      setAudits(a.items.map(e => e.action))
    } finally {
      setLoadingDetail(false)
    }
  }

  const toggleOpen = () => {
    setOpen(v => {
      const next = !v
      if (next) void loadExpandedData()
      return next
    })
  }

  const statusVariant = tenant.status === 'active' ? 'success' : tenant.status === 'suspended' ? 'warning' : 'danger'
  const planVariant   = tenant.plan_tier === 'enterprise' ? 'purple' : tenant.plan_tier === 'pro' ? 'blue' : 'default'

  return (
    <>
      <div className="grid grid-cols-[1.5fr_110px_110px_90px_90px_110px_170px_40px] items-center px-3 py-2.5 border-b border-black/[0.05] dark:border-white/[0.04] hover:bg-slate-50 dark:hover:bg-dark-bg3 transition-colors">
        <div>
          <div className="text-[12px] font-medium text-slate-900 dark:text-gray-100 truncate">{tenant.name}</div>
          <div className="text-[10px] text-slate-500 dark:text-gray-400 font-mono">{tenant.slug}</div>
        </div>
        <div><Badge variant={planVariant}>{tenant.plan_tier}</Badge></div>
        <div><Badge variant={statusVariant} dot>{tenant.status}</Badge></div>
        <div className="text-[11px] font-mono text-slate-500 dark:text-gray-400">{tenant.vm_count ?? '—'}</div>
        <div className="text-[11px] font-mono text-slate-500 dark:text-gray-400">{tenant.user_count ?? '—'}</div>
        <div className="text-[11px] font-mono text-slate-500 dark:text-gray-400">{tenant.storage_used_gb ?? 0} GB</div>
        <div className="flex gap-2">
          {tenant.status === 'active' ? (
            <Button size="sm" variant="danger" onClick={() => onSuspend(tenant.id, tenant.name)}>Suspend</Button>
          ) : (
            <Button size="sm" variant="secondary" onClick={() => onReinstate(tenant.id)}>Reinstate</Button>
          )}
        </div>
        <button onClick={toggleOpen} className="text-slate-400 dark:text-gray-500 hover:text-slate-700 dark:hover:text-gray-300">
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>

      {open && (
        <div className="px-4 py-3 border-b border-black/[0.05] dark:border-white/[0.04] bg-slate-50 dark:bg-dark-bg3">
          {loadingDetail ? (
            <div className="text-[12px] text-slate-500 dark:text-gray-400">Loading tenant detail…</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-[11px]">
              <Box title="Recent audits" lines={audits ?? ['No recent events']} />
              <Box
                title="Users"
                lines={
                  users === null
                    ? ['Endpoint unavailable']
                    : users.length
                    ? users.map(u => `${u.email} (${u.role})`)
                    : ['No users returned']
                }
              />
              <Box
                title="Limits"
                lines={detail
                  ? [
                      `vCPU: ${detail.max_vcpus ?? 0}`,
                      `RAM: ${detail.max_ram_gb ?? 0} GB`,
                      `Storage: ${detail.max_storage_gb ?? 0} GB`,
                    ]
                  : [
                      `vCPU: ${tenant.max_vcpus ?? 0}`,
                      `RAM: ${tenant.max_ram_gb ?? 0} GB`,
                      `Storage: ${tenant.max_storage_gb ?? 0} GB`,
                    ]
                }
              />
            </div>
          )}
        </div>
      )}
    </>
  )
}

function Box({ title, lines }: { title: string; lines: string[] }) {
  return (
    <div className="rounded-md border border-black/[0.06] dark:border-white/[0.06] bg-white dark:bg-dark-surface p-2">
      <div className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-gray-400 mb-1">{title}</div>
      <div className="space-y-0.5">
        {lines.map(line => <div key={line} className="font-mono text-[11px] text-slate-700 dark:text-gray-300">{line}</div>)}
      </div>
    </div>
  )
}
