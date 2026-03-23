import { useState } from 'react'
import { Download } from 'lucide-react'
import { useAudit } from '../hooks/useAudit'
import { exportAuditCSV } from '../api/audit'
import { PageHeader } from '../components/layout/PageHeader'
import { AuditFilters, type AuditFilterState } from '../components/audit/AuditFilters'
import { AuditTable } from '../components/audit/AuditTable'
import { Button } from '../components/ui/Button'
import { Select } from '../components/ui/Select'
import { useAuth } from '../contexts/AuthContext'

const DEFAULT_FILTERS: AuditFilterState = {
  action: '', resource_type: '', user_id: '', from_ts: '', to_ts: '',
}

export function AuditPage() {
  const { user, isMspAdmin } = useAuth()
  const [draft, setDraft] = useState<AuditFilterState>(DEFAULT_FILTERS)
  const [filters, setFilters] = useState<AuditFilterState>(DEFAULT_FILTERS)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)

  const auditQ = useAudit({
    page,
    page_size: pageSize,
    action: filters.action || undefined,
    resource_type: filters.resource_type || undefined,
    user_id: filters.user_id || undefined,
    from_ts: filters.from_ts ? new Date(filters.from_ts).toISOString() : undefined,
    to_ts: filters.to_ts ? new Date(filters.to_ts).toISOString() : undefined,
  })

  const total = auditQ.data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <div className="flex flex-col">
      <PageHeader
        title="Audit Log"
        subtitle="Immutable activity stream with integrity hashes"
        actions={
          <Button
            variant="primary"
            iconLeft={<Download size={13} />}
            onClick={() => exportAuditCSV({
              tenant_id: isMspAdmin ? user?.tenant_id : undefined,
              from_ts: filters.from_ts
                ? new Date(filters.from_ts).toISOString()
                : new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
              to_ts: filters.to_ts
                ? new Date(filters.to_ts).toISOString()
                : new Date().toISOString(),
            })}
          >
            Export CSV
          </Button>
        }
      />

      <div className="px-6 py-4 space-y-3">
        <AuditFilters
          value={draft}
          onChange={setDraft}
          onApply={() => { setFilters(draft); setPage(1) }}
          onReset={() => { setDraft(DEFAULT_FILTERS); setFilters(DEFAULT_FILTERS); setPage(1) }}
        />

        <div className="flex items-center justify-between gap-3 bg-white dark:bg-dark-surface border border-black/[0.07] dark:border-white/[0.07] rounded-xl p-3">
          <div className="text-[12px] text-slate-500 dark:text-gray-400">
            Showing page <span className="font-mono text-slate-700 dark:text-gray-300">{page}</span> of <span className="font-mono text-slate-700 dark:text-gray-300">{totalPages}</span> ({total} events)
          </div>
          <div className="flex items-center gap-2">
            <div className="w-[120px]">
              <Select
                value={String(pageSize)}
                onChange={e => { setPageSize(Number(e.target.value)); setPage(1) }}
                options={[
                  { value: '25', label: '25 / page' },
                  { value: '50', label: '50 / page' },
                  { value: '100', label: '100 / page' },
                ]}
              />
            </div>
            <Button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}>Previous</Button>
            <Button onClick={() => setPage(p => p + 1)} disabled={!auditQ.data?.has_more}>Next</Button>
          </div>
        </div>
        <AuditTable events={auditQ.data?.items ?? []} isLoading={auditQ.isLoading} />
      </div>
    </div>
  )
}
