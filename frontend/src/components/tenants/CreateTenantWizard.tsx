import { useState } from 'react'
import { Modal } from '../ui/Modal'
import { Input } from '../ui/Input'
import { Select } from '../ui/Select'
import { Button } from '../ui/Button'
import type { PlanTier, TenantCreate } from '../../types'

interface Props {
  open:     boolean
  onClose:  () => void
  onSubmit: (payload: TenantCreate) => Promise<void>
}

export function CreateTenantWizard({ open, onClose, onSubmit }: Props) {
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState<TenantCreate>({
    name: '','slug':'',plan_tier:'starter',admin_email:'',admin_password:'',admin_full_name:'',
  })

  const [step, setStep] = useState(1)

  const next = () => setStep(s => Math.min(3, s + 1))
  const back = () => setStep(s => Math.max(1, s - 1))

  const submit = async () => {
    setLoading(true)
    try {
      await onSubmit(form)
      setStep(1)
      setForm({ name: '', slug: '', plan_tier: 'starter', admin_email: '', admin_password: '', admin_full_name: '' })
      onClose()
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Create Tenant"
      width={620}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          {step > 1 && <Button onClick={back}>Back</Button>}
          {step < 3 ? <Button variant="primary" onClick={next}>Next</Button> : <Button variant="primary" loading={loading} onClick={submit}>Create tenant</Button>}
        </>
      }
    >
      <div className="text-[11px] text-slate-500 dark:text-gray-400">Step {step} of 3</div>

      {step === 1 && (
        <div className="grid grid-cols-1 gap-3">
          <Input label="Tenant name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
          <Input label="Slug" value={form.slug} onChange={e => setForm({ ...form, slug: e.target.value.toLowerCase() })} />
        </div>
      )}

      {step === 2 && (
        <div className="grid grid-cols-1 gap-3">
          <Select
            label="Plan tier"
            value={form.plan_tier}
            onChange={e => setForm({ ...form, plan_tier: e.target.value as PlanTier })}
            options={[
              { value: 'starter', label: 'Starter' },
              { value: 'pro', label: 'Pro' },
              { value: 'enterprise', label: 'Enterprise' },
            ]}
          />
          <Input label="First admin email" value={form.admin_email} onChange={e => setForm({ ...form, admin_email: e.target.value })} />
        </div>
      )}

      {step === 3 && (
        <div className="grid grid-cols-1 gap-3">
          <Input label="First admin password" type="password" value={form.admin_password} onChange={e => setForm({ ...form, admin_password: e.target.value })} />
          <Input label="First admin full name" value={form.admin_full_name ?? ''} onChange={e => setForm({ ...form, admin_full_name: e.target.value })} />
        </div>
      )}
    </Modal>
  )
}
