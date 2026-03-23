import type { ReactNode } from 'react'
import { clsx } from 'clsx'

type Accent = 'blue' | 'green' | 'amber' | 'purple'

const STRIPS: Record<Accent, string> = {
  blue:   'accent-strip-blue',
  green:  'accent-strip-green',
  amber:  'accent-strip-amber',
  purple: 'accent-strip-purple',
}

interface StatCardProps {
  label:    string
  value:    string | number
  delta?:   string
  deltaUp?: boolean
  accent?:  Accent
  icon?:    ReactNode
}

export function StatCard({ label, value, delta, deltaUp = true, accent = 'blue', icon }: StatCardProps) {
  return (
    <div className="relative bg-white dark:bg-dark-surface border border-black/[0.07] dark:border-white/[0.07] rounded-xl p-4 overflow-hidden">
      {/* Top accent strip */}
      <div className={clsx('absolute top-0 left-0 right-0 h-[2px] opacity-80', STRIPS[accent])} />

      {icon && (
        <div className="float-right text-slate-300 dark:text-gray-600 mt-0.5">{icon}</div>
      )}

      <div className="text-[10px] font-semibold uppercase tracking-[0.8px] text-slate-500 dark:text-gray-400 mb-1.5">
        {label}
      </div>
      <div className="font-mono text-[22px] font-medium text-slate-900 dark:text-gray-100 leading-none">
        {value}
      </div>
      {delta && (
        <div
          className={clsx(
            'text-[11px] mt-1',
            deltaUp ? 'text-success' : 'text-nova-danger'
          )}
        >
          {delta}
        </div>
      )}
    </div>
  )
}
