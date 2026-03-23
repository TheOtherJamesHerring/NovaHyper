import { lazy, Suspense } from 'react'
import { Cpu, Server, MemoryStick, HardDrive } from 'lucide-react'
import { useVMs } from '../hooks/useVMs'
import { useBackups } from '../hooks/useBackups'
import { StatCard } from '../components/charts/StatCard'
import { PageHeader } from '../components/layout/PageHeader'
import { Skeleton } from '../components/ui/Skeleton'

const DashboardCharts = lazy(() => import('../components/charts/DashboardCharts'))

export function DashboardPage() {
  const vmQ      = useVMs({ page: 1, page_size: 100 })
  const backupsQ = useBackups({ page: 1, page_size: 100 })

  const vms      = vmQ.data?.items ?? []
  const backups  = backupsQ.data?.items ?? []

  const running  = vms.filter(v => v.status === 'running').length
  const vcpus    = vms.reduce((s, v) => s + v.vcpus, 0)
  const ramGb    = Math.round(vms.reduce((s, v) => s + v.ram_mb, 0) / 1024)
  const diskGb   = vms.reduce((s, v) => s + v.disks.reduce((a, d) => a + d.size_gb, 0), 0)

  return (
    <div className="flex flex-col">
      <PageHeader
        title="Dashboard"
        subtitle="Realtime view across compute, protection, and storage"
      />

      <div className="px-6 py-4 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
        <StatCard label="Running VMs" value={running} delta="Live state" accent="blue" icon={<Server size={15} />} />
        <StatCard label="Total vCPUs allocated" value={vcpus} delta="Provisioned" accent="green" icon={<Cpu size={15} />} />
        <StatCard label="RAM allocated" value={`${ramGb} GB`} delta="Across all VMs" accent="amber" icon={<MemoryStick size={15} />} />
        <StatCard label="Storage used" value={`${(diskGb / 1024).toFixed(1)} TB`} delta="Post-dedup view" accent="purple" icon={<HardDrive size={15} />} />
      </div>

      <div className="px-6 pb-6">
        {vmQ.isLoading || backupsQ.isLoading ? (
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-3">
            <Skeleton className="xl:col-span-2 rounded-xl" height={220} />
            <Skeleton className="rounded-xl" height={220} />
            <Skeleton className="xl:col-span-3 rounded-xl" height={180} />
          </div>
        ) : (
          <Suspense fallback={<Skeleton className="rounded-xl" height={280} />}>
            <DashboardCharts vms={vms} backups={backups} />
          </Suspense>
        )}
      </div>
    </div>
  )
}
