import { useState } from 'react'
import { Plus } from 'lucide-react'
import { PageHeader } from '../components/layout/PageHeader'
import { Button } from '../components/ui/Button'
import { useTenants, useCreateTenant, useSuspendTenant, useReinstateTenant } from '../hooks/useTenants'
import { TenantTable } from '../components/tenants/TenantTable'
import { CreateTenantWizard } from '../components/tenants/CreateTenantWizard'
import type { TenantCreate } from '../types'

export function TenantsPage() {
  const [wizardOpen, setWizardOpen] = useState(false)
  const tenantsQ = useTenants(1, 100)
  const createM  = useCreateTenant()
  const suspendM = useSuspendTenant()
  const reinM    = useReinstateTenant()

  const handleCreate = async (payload: TenantCreate) => {
    await createM.mutateAsync(payload)
  }

  const handleSuspend = async (id: string, name: string) => {
    const typed = window.prompt(`Type tenant name to suspend: ${name}`)
    if (typed !== name) return
    await suspendM.mutateAsync({ id, reason: `Suspended by MSP admin for tenant ${name}` })
  }

  const handleReinstate = async (id: string) => {
    if (!window.confirm('Reinstate this tenant?')) return
    await reinM.mutateAsync({ id, reason: 'Reinstated by MSP admin' })
  }

  return (
    <div className="flex flex-col">
      <PageHeader
        title="Tenant Management"
        subtitle="MSP-wide tenant administration"
        actions={
          <Button variant="primary" iconLeft={<Plus size={13} />} onClick={() => setWizardOpen(true)}>
            Create Tenant
          </Button>
        }
      />

      <div className="px-6 py-4">
        <TenantTable
          tenants={tenantsQ.data?.items ?? []}
          isLoading={tenantsQ.isLoading}
          onSuspend={handleSuspend}
          onReinstate={handleReinstate}
        />
      </div>

      <CreateTenantWizard
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        onSubmit={handleCreate}
      />
    </div>
  )
}
