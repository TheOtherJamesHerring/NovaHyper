import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import { NotificationProvider, useNotifications } from './contexts/NotificationContext'
import { Sidebar } from './components/layout/Sidebar'
import { Topbar } from './components/layout/Topbar'
import { LoginPage } from './pages/Login'
import { DashboardPage } from './pages/Dashboard'
import { VMsPage } from './pages/VMs'
import { BackupsPage } from './pages/Backups'
import { AuditPage } from './pages/Audit'
import { TenantsPage } from './pages/Tenants'
import { SettingsPage } from './pages/Settings'
import { useBackups } from './hooks/useBackups'
import { useVMs } from './hooks/useVMs'

const queryClient = new QueryClient()

function ProtectedApp() {
  const { isAuthenticated, isMspAdmin } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <Topbar />
      <div className="flex flex-1 min-h-0 overflow-hidden">
        <Sidebar />
        <main className="flex-1 min-h-0 overflow-auto">
          <Routes>
            <Route path="/"         element={<DashboardPage />} />
            <Route path="/vms"      element={<VMsPage />} />
            <Route path="/backups"  element={<BackupsPage />} />
            <Route path="/audit"    element={<AuditPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route
              path="/tenants"
              element={isMspAdmin ? <TenantsPage /> : <Navigate to="/" replace />}
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
      <NotificationFeed />
    </div>
  )
}

/* Poll every 30s and generate client-side notifications */
function NotificationFeed() {
  const { push } = useNotifications()
  const backupsQ = useBackups({ page: 1, page_size: 50 }, { refetchInterval: 30_000 })
  const vmsQ     = useVMs({ page: 1, page_size: 100 }, { refetchInterval: 30_000 })

  const lastBackupSeen = useRef<string>('')
  const erroredVMSet   = useRef<Set<string>>(new Set())

  useEffect(() => {
    const backups = backupsQ.data?.items ?? []
    if (!backups.length) return
    const sorted = [...backups].sort((a, b) => (b.created_at > a.created_at ? 1 : -1))

    if (!lastBackupSeen.current) {
      lastBackupSeen.current = sorted[0].id
      return
    }

    for (const job of sorted) {
      if (job.id === lastBackupSeen.current) break
      if (job.status === 'success') {
        push('success', 'Backup completed', `Backup ${job.id.slice(0, 8)} finished successfully`, 'backup')
      }
      if (job.status === 'failed') {
        push('error', 'Backup failed', job.error_message ?? `Backup ${job.id.slice(0, 8)} failed`, 'backup')
      }
    }

    lastBackupSeen.current = sorted[0].id
  }, [backupsQ.data, push])

  useEffect(() => {
    const vms = vmsQ.data?.items ?? []
    const nextSet = new Set(vms.filter(v => v.status === 'error').map(v => v.id))

    nextSet.forEach(id => {
      if (!erroredVMSet.current.has(id)) {
        const vm = vms.find(v => v.id === id)
        if (vm) push('error', 'VM error state', `${vm.name} entered error state`, 'vm')
      }
    })

    erroredVMSet.current = nextSet
  }, [vmsQ.data, push])

  return null
}

function PublicOnly({ children }: { children: JSX.Element }) {
  const { isAuthenticated } = useAuth()
  if (isAuthenticated) return <Navigate to="/" replace />
  return children
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<PublicOnly><LoginPage /></PublicOnly>} />
      <Route path="/*" element={<ProtectedApp />} />
    </Routes>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <NotificationProvider>
            <BrowserRouter>
              <AppRoutes />
            </BrowserRouter>
          </NotificationProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
