import { PageHeader } from '../components/layout/PageHeader'
import { BackupPanel } from '../components/backups/BackupPanel'

export function BackupsPage() {
  return (
    <div className="flex flex-col">
      <PageHeader
        title="Backups"
        subtitle="Track backup jobs in real time and inspect manifests"
      />
      <div className="px-6 py-4">
        <BackupPanel />
      </div>
    </div>
  )
}
