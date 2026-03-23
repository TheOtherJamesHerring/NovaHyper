import { clsx } from 'clsx'
import type { ReactNode } from 'react'

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'purple' | 'blue' | 'teal'

interface BadgeProps {
  variant?:  BadgeVariant
  dot?:      boolean
  children:  ReactNode
  className?: string
}

const VARIANTS: Record<BadgeVariant, string> = {
  default: 'bg-slate-100 dark:bg-dark-bg3 text-slate-600 dark:text-gray-400',
  success: 'bg-[rgba(56,217,169,0.12)] text-success',
  warning: 'bg-[rgba(245,158,11,0.12)] text-nova-warn',
  danger:  'bg-[rgba(239,68,68,0.12)]  text-nova-danger',
  purple:  'bg-[rgba(167,139,250,0.12)] text-nova-purple',
  blue:    'bg-[rgba(79,142,247,0.12)]  text-accent',
  teal:    'bg-[rgba(56,217,169,0.12)]  text-success',
}

export function Badge({ variant = 'default', dot, children, className }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium',
        VARIANTS[variant],
        className
      )}
    >
      {dot && (
        <span
          className="w-1.5 h-1.5 rounded-full bg-current opacity-80"
          aria-hidden
        />
      )}
      {children}
    </span>
  )
}
