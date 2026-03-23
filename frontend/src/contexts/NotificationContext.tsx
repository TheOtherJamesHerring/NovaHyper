import {
  createContext,
  useContext,
  useReducer,
  useCallback,
  useRef,
  type ReactNode,
} from 'react'
import type { Notification, NotificationType, NotificationSource } from '../types'

/* ── Reducer ─────────────────────────────────────────────────────────────── */
type Action =
  | { type: 'ADD';       payload: Notification }
  | { type: 'READ';      id: string }
  | { type: 'READ_ALL' }
  | { type: 'DISMISS';   id: string }

function reducer(state: Notification[], action: Action): Notification[] {
  switch (action.type) {
    case 'ADD':
      return [action.payload, ...state].slice(0, 50)  // cap at 50
    case 'READ':
      return state.map(n => n.id === action.id ? { ...n, read: true } : n)
    case 'READ_ALL':
      return state.map(n => ({ ...n, read: true }))
    case 'DISMISS':
      return state.filter(n => n.id !== action.id)
  }
}

/* ── Context ─────────────────────────────────────────────────────────────── */
interface NotificationContextValue {
  notifications:  Notification[]
  unreadCount:    number
  push:           (type: NotificationType, title: string, message: string, source: NotificationSource) => void
  markRead:       (id: string) => void
  markAllRead:    () => void
  dismiss:        (id: string) => void
}

const NotificationContext = createContext<NotificationContextValue | null>(null)

export function NotificationProvider({ children }: { children: ReactNode }) {
  const [notifications, dispatch] = useReducer(reducer, [])
  const idCounter = useRef(0)

  const push = useCallback(
    (type: NotificationType, title: string, message: string, source: NotificationSource) => {
      dispatch({
        type:    'ADD',
        payload: {
          id:        `notif-${++idCounter.current}`,
          type,
          title,
          message,
          timestamp: Date.now(),
          read:      false,
          source,
        },
      })
    },
    []
  )

  const markRead    = useCallback((id: string) => dispatch({ type: 'READ', id }), [])
  const markAllRead = useCallback(() => dispatch({ type: 'READ_ALL' }), [])
  const dismiss     = useCallback((id: string) => dispatch({ type: 'DISMISS', id }), [])

  const unreadCount = notifications.filter(n => !n.read).length

  return (
    <NotificationContext.Provider
      value={{ notifications, unreadCount, push, markRead, markAllRead, dismiss }}
    >
      {children}
    </NotificationContext.Provider>
  )
}

export function useNotifications(): NotificationContextValue {
  const ctx = useContext(NotificationContext)
  if (!ctx) throw new Error('useNotifications must be used within NotificationProvider')
  return ctx
}
