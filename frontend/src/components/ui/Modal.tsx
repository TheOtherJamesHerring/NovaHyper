import { useEffect, useCallback, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import { clsx } from 'clsx'

interface ModalProps {
  open:      boolean
  onClose:   () => void
  title?:    string
  children:  ReactNode
  footer?:   ReactNode
  width?:    number
  className?: string
}

export function Modal({ open, onClose, title, children, footer, width = 520, className }: ModalProps) {
  /* Close on Escape */
  const handleKey = useCallback(
    (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() },
    [onClose]
  )
  useEffect(() => {
    if (open) document.addEventListener('keydown', handleKey)
    return ()  => document.removeEventListener('keydown', handleKey)
  }, [open, handleKey])

  /* Lock body scroll */
  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [open])

  if (!open) return null

  return createPortal(
    <div
      className="fixed inset-0 z-[1000] flex items-center justify-center p-4"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" />

      {/* Modal surface */}
      <div
        style={{ width, maxWidth: '95vw' }}
        className={clsx(
          'relative z-10 flex flex-col max-h-[90vh]',
          'bg-white dark:bg-dark-bg2',
          'border border-black/[0.08] dark:border-white/[0.12]',
          'rounded-xl shadow-[0_20px_60px_rgba(0,0,0,0.5)]',
          'animate-[modalIn_0.18s_ease]',
          className
        )}
      >
        {/* Header */}
        {title && (
          <div className="flex items-center justify-between px-5 py-4 border-b border-black/[0.06] dark:border-white/[0.07] shrink-0">
            <h2 className="font-display text-[15px] font-semibold text-slate-900 dark:text-gray-100">
              {title}
            </h2>
            <button
              onClick={onClose}
              className="p-1 rounded text-slate-400 dark:text-gray-500 hover:text-slate-700 dark:hover:text-gray-200 hover:bg-slate-100 dark:hover:bg-dark-surface transition-colors"
            >
              <X size={16} />
            </button>
          </div>
        )}

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-4">
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div className="shrink-0 flex justify-end gap-2 px-5 py-3.5 border-t border-black/[0.06] dark:border-white/[0.07]">
            {footer}
          </div>
        )}
      </div>

      <style>{`
        @keyframes modalIn {
          from { opacity: 0; transform: translateY(12px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>,
    document.body
  )
}
