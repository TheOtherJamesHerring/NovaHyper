import { PageHeader } from '../components/layout/PageHeader'

export function SettingsPage() {
  return (
    <div className="flex flex-col">
      <PageHeader title="Settings" subtitle="Platform and profile preferences" />
      <div className="px-6 py-4 text-[13px] text-slate-500 dark:text-gray-400">Settings UI can be expanded here.</div>
    </div>
  )
}
