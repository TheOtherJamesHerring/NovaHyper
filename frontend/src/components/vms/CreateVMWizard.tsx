import { useState, type FormEvent } from 'react'
import { clsx } from 'clsx'
import { Check } from 'lucide-react'
import type { VMCreate, DiskFormat } from '../../types'
import { Modal } from '../ui/Modal'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { Select } from '../ui/Select'
import {
  OS_ICON_MAP, OS_LABEL_MAP, OS_SUB_MAP, type OsKey, getOsKey,
} from './OsIcons'

/* ── Slider snap values ── */
const VCPU_SNAPS  = [1, 2, 4, 8, 16, 32, 64, 128, 256]
const RAM_SNAPS_MB= [512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144]

function ramLabel(mb: number): string {
  if (mb < 1024) return `${mb} MB`
  const gb = mb / 1024
  return `${gb % 1 === 0 ? gb : gb.toFixed(0)} GB`
}

/* ── Step indicator ── */
const STEPS = ['Name & OS', 'Resources', 'Storage & Network', 'Review']

function StepIndicator({ step }: { step: number }) {
  return (
    <div className="flex items-center gap-0 mb-6">
      {STEPS.map((label, i) => (
        <div key={i} className="flex items-center flex-1 last:flex-none">
          <div className="flex flex-col items-center">
            <div className={clsx(
              'w-7 h-7 rounded-full flex items-center justify-center text-[12px] font-semibold shrink-0',
              i < step  ? 'bg-accent text-white' :
              i === step ? 'bg-accent text-white ring-4 ring-accent/20' :
                           'bg-slate-100 dark:bg-dark-bg3 text-slate-400 dark:text-gray-500'
            )}>
              {i < step ? <Check size={14} /> : i + 1}
            </div>
            <span className={clsx('text-[10px] mt-1 text-center w-16 truncate', i === step ? 'text-accent' : 'text-slate-400 dark:text-gray-500')}>
              {label}
            </span>
          </div>
          {i < STEPS.length - 1 && (
            <div className={clsx('flex-1 h-px mx-1 mb-5', i < step ? 'bg-accent' : 'bg-slate-200 dark:bg-dark-bg3')} />
          )}
        </div>
      ))}
    </div>
  )
}

/* ── OS picker grid ── */
const OS_OPTIONS: OsKey[] = ['windows', 'ubuntu', 'debian', 'rhel', 'linux', 'freebsd', 'custom']

function OsPicker({ value, onChange }: { value: OsKey; onChange: (k: OsKey) => void }) {
  return (
    <div className="grid grid-cols-3 gap-2">
      {OS_OPTIONS.map(key => {
        const Icon = OS_ICON_MAP[key]
        return (
          <button
            key={key}
            type="button"
            onClick={() => onChange(key)}
            className={clsx(
              'flex flex-col items-center gap-1 p-3 rounded-lg border text-center transition-colors',
              value === key
                ? 'border-accent bg-accent/[0.07] dark:bg-accent/[0.08]'
                : 'border-black/[0.07] dark:border-white/[0.07] hover:border-accent hover:bg-slate-50 dark:hover:bg-dark-bg3'
            )}
          >
            <Icon width={28} height={28} />
            <span className="text-[12px] font-medium text-slate-800 dark:text-gray-200">{OS_LABEL_MAP[key]}</span>
            <span className="text-[10px] text-slate-400 dark:text-gray-500">{OS_SUB_MAP[key]}</span>
          </button>
        )
      })}
    </div>
  )
}

/* ── Slider component ── */
function SnapSlider({
  label, snaps, value, onChange, format,
}: {
  label:    string
  snaps:    number[]
  value:    number
  onChange: (v: number) => void
  format:   (v: number) => string
}) {
  const idx     = snaps.indexOf(value)
  const max     = snaps.length - 1

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-gray-400">{label}</label>
        <span className="font-mono text-[13px] text-accent font-medium">{format(value)}</span>
      </div>
      <input
        type="range"
        min={0}
        max={max}
        step={1}
        value={idx < 0 ? 0 : idx}
        onChange={e => onChange(snaps[Number(e.target.value)])}
        className="w-full accent-accent"
      />
      <div className="flex justify-between text-[10px] text-slate-400 dark:text-gray-500">
        <span>{format(snaps[0])}</span>
        <span>{format(snaps[max])}</span>
      </div>
    </div>
  )
}

/* ── Form state ── */
interface WizardState {
  name:          string
  osKey:         OsKey
  vcpus:         number
  ram_mb:        number
  disk_gb:       number
  disk_format:   DiskFormat
  storage_pool:  string
  network:       string
  backup_policy: string
  description:   string
}

const INIT: WizardState = {
  name:          '',
  osKey:         'linux',
  vcpus:         4,
  ram_mb:        4096,
  disk_gb:       80,
  disk_format:   'qcow2',
  storage_pool:  '11111111-1111-4111-8111-111111111112',
  network:       'default',
  backup_policy: 'daily',
  description:   '',
}

/* ── Step validation ── */
function validateStep(step: number, state: WizardState): string | null {
  if (step === 0 && !state.name.trim()) return 'VM name is required'
  if (step === 0 && !/^[a-z0-9-]+$/.test(state.name)) return 'Name must be lowercase letters, digits, and hyphens only'
  if (step === 1 && state.vcpus < 1)   return 'vCPUs must be at least 1'
  if (step === 1 && state.ram_mb < 512) return 'RAM must be at least 512 MB'
  if (step === 2 && state.disk_gb < 10) return 'Disk must be at least 10 GB'
  return null
}

/* ── Main wizard ── */
interface CreateVMWizardProps {
  open:    boolean
  onClose: () => void
  onSubmit:(data: VMCreate) => Promise<void>
  loading?: boolean
}

export function CreateVMWizard({ open, onClose, onSubmit, loading }: CreateVMWizardProps) {
  const [step, setStep]     = useState(0)
  const [form, setForm]     = useState<WizardState>(INIT)
  const [error, setError]   = useState<string | null>(null)

  const set = (patch: Partial<WizardState>) => setForm(prev => ({ ...prev, ...patch }))

  const next = () => {
    const err = validateStep(step, form)
    if (err) { setError(err); return }
    setError(null)
    setStep(s => Math.min(s + 1, STEPS.length - 1))
  }
  const back = () => { setError(null); setStep(s => Math.max(s - 1, 0)) }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const err = validateStep(step, form)
    if (err) { setError(err); return }
    const payload: VMCreate = {
      name:        form.name,
      description: form.description || undefined,
      vcpus:       form.vcpus,
      ram_mb:      form.ram_mb,
      os_type:     ['windows'].includes(form.osKey) ? 'windows' : form.osKey === 'freebsd' ? 'bsd' : 'linux',
      os_variant:  form.osKey,
      host_id:     '11111111-1111-4111-8111-111111111111',
      disks: [{
        size_gb:         form.disk_gb,
        disk_format:     form.disk_format,
        storage_pool_id: form.storage_pool,
      }],
      network_id: form.network,
      backup_policy: form.backup_policy !== 'none' ? { schedule: form.backup_policy } : {},
    }
    await onSubmit(payload)
    setStep(0)
    setForm(INIT)
  }

  const closeAndReset = () => {
    setStep(0)
    setForm(INIT)
    setError(null)
    onClose()
  }

  return (
    <Modal
      open={open}
      onClose={closeAndReset}
      title="Create Virtual Machine"
      width={560}
      footer={
        <>
          <Button variant="secondary" onClick={step === 0 ? closeAndReset : back}>{step === 0 ? 'Cancel' : 'Back'}</Button>
          {step < STEPS.length - 1
            ? <Button variant="primary" onClick={next}>Next</Button>
            : <Button variant="primary" loading={loading} onClick={handleSubmit as unknown as React.MouseEventHandler}>Create VM</Button>
          }
        </>
      }
    >
      <StepIndicator step={step} />

      {error && (
        <div className="px-3 py-2 rounded-md bg-nova-danger/10 border border-nova-danger/20 text-nova-danger text-[12px]">
          {error}
        </div>
      )}

      {/* Step 0: Name + OS */}
      {step === 0 && (
        <div className="flex flex-col gap-4">
          <Input
            label="VM Name"
            placeholder="e.g. web-prod-05"
            value={form.name}
            onChange={e => set({ name: e.target.value.toLowerCase() })}
            autoFocus
          />
          <Input
            label="Description (optional)"
            placeholder="Brief description"
            value={form.description}
            onChange={e => set({ description: e.target.value })}
          />
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-gray-400 mb-2">
              Operating System
            </div>
            <OsPicker value={form.osKey} onChange={k => set({ osKey: k })} />
          </div>
        </div>
      )}

      {/* Step 1: Resources */}
      {step === 1 && (
        <div className="flex flex-col gap-5">
          <SnapSlider
            label="vCPUs"
            snaps={VCPU_SNAPS}
            value={form.vcpus}
            onChange={v => set({ vcpus: v })}
            format={v => `${v} vCPU${v > 1 ? 's' : ''}`}
          />
          <SnapSlider
            label="RAM"
            snaps={RAM_SNAPS_MB}
            value={form.ram_mb}
            onChange={v => set({ ram_mb: v })}
            format={ramLabel}
          />
        </div>
      )}

      {/* Step 2: Storage + Network */}
      {step === 2 && (
        <div className="flex flex-col gap-4">
          <div className="flex gap-3 items-end">
            <Input
              label="Primary disk (GB)"
              type="number"
              min={10}
              max={65536}
              value={form.disk_gb}
              onChange={e => set({ disk_gb: Number(e.target.value) })}
              className="w-32"
            />
            <Select
              label="Format"
              value={form.disk_format}
              onChange={e => set({ disk_format: e.target.value as DiskFormat })}
              options={[
                { value: 'qcow2', label: 'qcow2 (thin)' },
                { value: 'raw',   label: 'raw (full)'  },
              ]}
            />
          </div>
          <Select
            label="Storage pool"
            value={form.storage_pool}
            onChange={e => set({ storage_pool: e.target.value })}
            options={[
              { value: '11111111-1111-4111-8111-111111111112', label: 'ZFS tank0 — local · 8.2 TB free' },
            ]}
          />
          <Select
            label="Network"
            value={form.network}
            onChange={e => set({ network: e.target.value })}
            options={[
              { value: 'default',  label: 'VLAN 100 — Production' },
              { value: 'staging',  label: 'VLAN 200 — Staging'    },
              { value: 'mgmt',     label: 'VLAN 300 — Management' },
            ]}
          />
        </div>
      )}

      {/* Step 3: Backup policy + Review */}
      {step === 3 && (
        <div className="flex flex-col gap-4">
          <Select
            label="Backup policy"
            value={form.backup_policy}
            onChange={e => set({ backup_policy: e.target.value })}
            options={[
              { value: 'daily',   label: 'Daily incremental + weekly full' },
              { value: 'hourly',  label: 'Hourly incremental'              },
              { value: 'weekly',  label: 'Weekly full only'                },
              { value: 'none',    label: 'No backup'                       },
            ]}
          />

          <div className="bg-slate-50 dark:bg-dark-bg3 rounded-lg p-4 text-[12px] flex flex-col gap-2">
            <div className="font-semibold text-slate-700 dark:text-gray-200 mb-1">Review summary</div>
            {[
              ['Name',         form.name || '—'],
              ['OS',           `${OS_LABEL_MAP[form.osKey]} (${OS_SUB_MAP[form.osKey]})`],
              ['vCPUs',        `${form.vcpus}`],
              ['RAM',          ramLabel(form.ram_mb)],
              ['Disk',         `${form.disk_gb} GB (${form.disk_format})`],
              ['Storage pool', form.storage_pool],
              ['Network',      form.network],
              ['Backup',       form.backup_policy],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <span className="text-slate-500 dark:text-gray-400">{k}</span>
                <span className="font-mono text-slate-800 dark:text-gray-200">{v}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Modal>
  )
}
