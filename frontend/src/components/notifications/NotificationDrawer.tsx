import { createPortal } from 'react-dom'
import { X, CheckCheck, Bell, CheckCircle, AlertCircle, XCircle, Info } from 'lucide-react'
import { clsx } from 'clsx'
import type { Notification } from '../../types'

const TYPE_ICON = {
  success: <CheckCircle size={14} className="text-success" />,
  warning: <AlertCircle size={14} className="text-nova-warn" />,
  error:   <XCircle     size={14} className="text-nova-danger" />,
  info:    <Info        size={14} className="text-accent" />,
} as const

interface Props {
  open:          boolean
  onClose:       () => void
  notifications: Notification[]
  onMarkRead:    (id: string) => void
  onMarkAllRead: () => void
  onDismiss:     (id: string) => void
  formatTime:    (iso: string) => string
}

export function NotificationDrawer({
  open, onClose, notifications, onMarkRead, onMarkAllRead, onDismiss, formatTime,
}: Props) {
  return createPortal(
    <>
      {/* Backdrop */}
      <div
        className={clsx(
          'fixed inset-0 z-[900] transition-opacity',
          open ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        )}
        style={{ background: 'rgba(0,0,0,0.3)' }}
        onClick={onClose}
      />

      {/* Drawer */}
      <aside
        className={clsx(
          'fixed top-0 right-0 h-full z-[901] w-80 flex flex-col',
          'bg-white dark:bg-dark-bg2',
          'border-l border-black/[0.08] dark:border-white/[0.07]',
          'shadow-2xl transition-transform duration-200',
          open ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        {/* Header */}
        <div className="flex items-center gap-2 px-4 py-3.5 border-b border-black/[0.06] dark:border-white/[0.07]">
          <Bell size={14} className="text-slate-400 dark:text-gray-500" />
          <span className="flex-1 font-display text-[14px] font-semibold text-slate-900 dark:text-gray-100">
            Notifications
          </span>
          <button
            onClick={onMarkAllRead}
            className="flex items-center gap-1 text-[11px] text-accent hover:underline"
          >
            <CheckCheck size={12} /> Read all
          </button>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-700 dark:hover:text-gray-200 hover:bg-slate-100 dark:hover:bg-dark-bg3"
          >
            <X size={14} />
          </button>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 gap-2 text-slate-400 dark:text-gray-500">
              <Bell size={32} strokeWidth={1} />
              <span className="text-[12px]">No notifications</span>
            </div>
          ) : (
            notifications.map(n => (
              <div
                key={n.id}
                onClick={() => onMarkRead(n.id)}
                className={clsx(
                  'flex gap-3 px-4 py-3 border-b border-black/[0.04] dark:border-white/[0.04] cursor-pointer',
                  'hover:bg-slate-50 dark:hover:bg-dark-bg3 transition-colors',
                  !n.read && 'bg-accent/[0.04] dark:bg-accent/[0.05]'
                )}
              >
                <span className="mt-0.5 shrink-0">{TYPE_ICON[n.type]}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className={clsx('text-[12px] font-medium truncate', !n.read && 'text-slate-900 dark:text-gray-100')}>
                      {n.title}
                    </span>
                    {!n.read && <span className="w-1.5 h-1.5 rounded-full bg-accent shrink-0" />}
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-gray-400 mt-0.5 line-clamp-2">{n.message}</p>
                  <span className="text-[10px] text-slate-400 dark:text-gray-500 mt-1 block">
                    {formatTime(new Date(n.timestamp).toISOString())}
                  </span>
                </div>
                <button
                  onClick={e => { e.stopPropagation(); onDismiss(n.id) }}
                  className="shrink-0 p-0.5 rounded text-slate-300 dark:text-gray-600 hover:text-slate-500 dark:hover:text-gray-400"
                >
                  <X size={12} />
                </button>
              </div>
            ))
          )}
        </div>
      </aside>
    </>,
    document.body
  )
}
