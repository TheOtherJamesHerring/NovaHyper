import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useVMs, useCreateVM, useVMAction } from '../hooks/useVMs'
import { PageHeader } from '../components/layout/PageHeader'
import { Button } from '../components/ui/Button'
import { VMTable } from '../components/vms/VMTable'
import { CreateVMWizard } from '../components/vms/CreateVMWizard'
import type { VMCreate, VMResponse } from '../types'

export function VMsPage() {
  const [wizardOpen, setWizardOpen] = useState(false)
  const vmQ       = useVMs({ page: 1, page_size: 300 })
  const createM   = useCreateVM()
  const actionM   = useVMAction()

  const onCreate = async (payload: VMCreate) => {
    await createM.mutateAsync(payload)
  }

  const onAction = async (action: string, vm: VMResponse) => {
    await actionM.mutateAsync({ id: vm.id, body: { action: action as any } })
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      <PageHeader
        title="Virtual Machines"
        subtitle={`${vmQ.data?.total ?? 0} VMs across your KVM estate`}
        actions={
          <Button variant="primary" iconLeft={<Plus size={13} />} onClick={() => setWizardOpen(true)}>
            Create VM
          </Button>
        }
      />

      <div className="px-6 py-4 flex-1 min-h-0">
        <VMTable
          vms={vmQ.data?.items ?? []}
          isLoading={vmQ.isLoading}
          onAction={onAction}
          onRefresh={() => vmQ.refetch()}
        />
      </div>

      <CreateVMWizard
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        onSubmit={onCreate}
      />
    </div>
  )
}
