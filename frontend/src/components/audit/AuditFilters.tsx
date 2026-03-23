import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { Select } from '../ui/Select'

export interface AuditFilterState {
  action:        string
  resource_type: string
  user_id:       string
  from_ts:       string
  to_ts:         string
}

interface Props {
  value:     AuditFilterState
  onChange:  (next: AuditFilterState) => void
  onApply:   () => void
  onReset:   () => void
}

const ACTIONS = [
  '',
  'vm.create', 'vm.delete', 'vm.action',
  'backup.create', 'backup.cancel', 'backup.delete',
  'tenant.create', 'tenant.update', 'tenant.suspend', 'tenant.reinstate', 'tenant.delete',
  'auth.login', 'auth.login_failed',
]

const RESOURCES = ['', 'vm', 'backup', 'tenant', 'auth', 'user']

function toLocalInputValue(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  const y = date.getFullYear()
  const m = pad(date.getMonth() + 1)
  const d = pad(date.getDate())
  const hh = pad(date.getHours())
  const mm = pad(date.getMinutes())
  return `${y}-${m}-${d}T${hh}:${mm}`
}

export function AuditFilters({ value, onChange, onApply, onReset }: Props) {
  const now = new Date()
  const applyPreset = (hours: number) => {
    const from = new Date(now.getTime() - hours * 60 * 60 * 1000)
    onChange({ ...value, from_ts: toLocalInputValue(from), to_ts: toLocalInputValue(now) })
  }

  const rangeInvalid = Boolean(value.from_ts && value.to_ts && value.from_ts > value.to_ts)

  return (
    <div className="grid grid-cols-1 md:grid-cols-5 gap-2 bg-white dark:bg-dark-surface border border-black/[0.07] dark:border-white/[0.07] rounded-xl p-3">
      <Select
        label="Action"
        value={value.action}
        onChange={e => onChange({ ...value, action: e.target.value })}
        options={ACTIONS.map(a => ({ value: a, label: a || 'All actions' }))}
      />
      <Select
        label="Resource"
        value={value.resource_type}
        onChange={e => onChange({ ...value, resource_type: e.target.value })}
        options={RESOURCES.map(r => ({ value: r, label: r || 'All resources' }))}
      />
      <Input
        label="User ID"
        value={value.user_id}
        onChange={e => onChange({ ...value, user_id: e.target.value })}
        placeholder="optional"
      />
      <Input
        label="From"
        type="datetime-local"
        value={value.from_ts}
        onChange={e => onChange({ ...value, from_ts: e.target.value })}
      />
      <Input
        label="To"
        type="datetime-local"
        value={value.to_ts}
        onChange={e => onChange({ ...value, to_ts: e.target.value })}
      />

      <div className="md:col-span-5 flex items-center justify-between mt-1">
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-gray-400">Presets</span>
          <Button size="sm" onClick={() => applyPreset(24)}>Last 24h</Button>
          <Button size="sm" onClick={() => applyPreset(24 * 7)}>Last 7d</Button>
          <Button size="sm" onClick={() => applyPreset(24 * 30)}>Last 30d</Button>
        </div>
        {rangeInvalid && <span className="text-[11px] text-nova-danger">From must be before To</span>}
      </div>

      <div className="md:col-span-5 flex justify-end gap-2 mt-1">
        <Button onClick={onReset}>Reset</Button>
        <Button variant="primary" onClick={onApply} disabled={rangeInvalid}>Apply</Button>
      </div>
    </div>
  )
}
