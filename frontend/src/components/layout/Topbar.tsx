import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Sun, Moon, Bell, LogOut, ChevronDown } from 'lucide-react'
import { clsx } from 'clsx'
import { useAuth } from '../../contexts/AuthContext'
import { useTheme } from '../../contexts/ThemeContext'
import { useNotifications } from '../../contexts/NotificationContext'
import { NotificationDrawer } from '../notifications/NotificationDrawer'
import { formatRelativeTime } from '../../utils/format'

export function Topbar() {
  const { user, logout }                 = useAuth()
  const { isDark, toggle: toggleTheme }  = useTheme()
  const { unreadCount, notifications, markRead, markAllRead, dismiss } = useNotifications()
  const [drawerOpen, setDrawerOpen]      = useState(false)
  const [userMenuOpen, setUserMenuOpen]  = useState(false)
  const navigate                         = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const initials = user?.role === 'msp_admin' ? 'MSP' : (user?.id ?? '??').slice(0, 2).toUpperCase()

  return (
    <>
      <header className="h-[52px] shrink-0 flex items-center gap-3 px-5 bg-white dark:bg-dark-bg2 border-b border-black/[0.06] dark:border-white/[0.07] z-50">
        {/* Logo */}
        <span className="font-display text-[17px] font-bold tracking-[-0.5px] text-slate-900 dark:text-gray-100 select-none">
          Nova<span className="text-accent">Hyper</span>
        </span>

        {/* Tenant badge */}
        {user && (
          <span className="flex items-center gap-1.5 bg-slate-100 dark:bg-dark-surface border border-black/[0.07] dark:border-white/[0.1] rounded px-2.5 py-1 font-mono text-[11px] text-success">
            <span className="w-1.5 h-1.5 rounded-full bg-success shadow-[0_0_6px_theme(colors.success)]" />
            {user.role === 'msp_admin' ? 'MSP Admin' : `Tenant: ${user.tenant_id.slice(0, 8)}`}
          </span>
        )}

        <div className="flex-1" />

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-md text-slate-500 dark:text-gray-400 hover:text-slate-700 dark:hover:text-gray-200 hover:bg-slate-100 dark:hover:bg-dark-bg3 transition-colors"
          title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {isDark ? <Sun size={15} /> : <Moon size={15} />}
        </button>

        {/* Bell */}
        <button
          onClick={() => setDrawerOpen(true)}
          className="relative p-2 rounded-md text-slate-500 dark:text-gray-400 hover:text-slate-700 dark:hover:text-gray-200 hover:bg-slate-100 dark:hover:bg-dark-bg3 transition-colors"
          title="Notifications"
        >
          <Bell size={15} />
          {unreadCount > 0 && (
            <span className="absolute top-1 right-1 min-w-[14px] h-[14px] rounded-full bg-nova-danger text-white text-[9px] font-bold flex items-center justify-center px-0.5">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </button>

        {/* User avatar / menu */}
        <div className="relative">
          <button
            onClick={() => setUserMenuOpen(v => !v)}
            className="flex items-center gap-1.5 group"
          >
            <span className="w-7 h-7 rounded-full bg-gradient-to-br from-accent to-nova-purple flex items-center justify-center text-white text-[10px] font-semibold select-none">
              {initials}
            </span>
            <ChevronDown size={12} className="text-slate-400 dark:text-gray-500 group-hover:text-slate-600 dark:group-hover:text-gray-300" />
          </button>

          {userMenuOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setUserMenuOpen(false)} />
              <div className="absolute right-0 top-full mt-1 z-50 w-52 bg-white dark:bg-dark-bg2 border border-black/[0.08] dark:border-white/[0.1] rounded-lg shadow-xl overflow-hidden">
                <div className="px-3 py-2 border-b border-black/[0.05] dark:border-white/[0.07]">
                  <div className="text-[12px] font-medium text-slate-900 dark:text-gray-100">{user?.role}</div>
                  <div className="text-[11px] text-slate-500 dark:text-gray-400 font-mono truncate">{user?.id}</div>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 w-full px-3 py-2 text-[13px] text-nova-danger hover:bg-slate-50 dark:hover:bg-dark-bg3 transition-colors"
                >
                  <LogOut size={13} />
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </header>

      <NotificationDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        notifications={notifications}
        onMarkRead={markRead}
        onMarkAllRead={markAllRead}
        onDismiss={dismiss}
        formatTime={formatRelativeTime}
      />
    </>
  )
}
