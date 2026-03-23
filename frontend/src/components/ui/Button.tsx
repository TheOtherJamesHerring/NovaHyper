import { type ButtonHTMLAttributes, forwardRef } from 'react'
import { clsx } from 'clsx'
import { Spinner } from './Spinner'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
export type ButtonSize    = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:  ButtonVariant
  size?:     ButtonSize
  loading?:  boolean
  iconLeft?: React.ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'secondary', size = 'md', loading, iconLeft, className, children, disabled, ...rest }, ref) => {
    const base = 'inline-flex items-center justify-center gap-1.5 font-medium rounded-md transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent'

    const variants: Record<ButtonVariant, string> = {
      primary:   'bg-accent text-white hover:bg-[#3a7de0] disabled:opacity-60',
      secondary: 'bg-white dark:bg-dark-surface border border-black/[0.08] dark:border-white/[0.07] text-slate-700 dark:text-gray-200 hover:border-accent hover:bg-slate-50 dark:hover:bg-dark-bg3',
      ghost:     'text-slate-600 dark:text-gray-400 hover:bg-slate-100 dark:hover:bg-dark-bg3',
      danger:    'bg-nova-danger text-white hover:bg-[#dc2626]',
    }

    const sizes: Record<ButtonSize, string> = {
      sm: 'text-[11px] px-2.5 py-1.5',
      md: 'text-[12px] px-3.5 py-[7px]',
      lg: 'text-[13px] px-4 py-2',
    }

    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={clsx(base, variants[variant], sizes[size], className)}
        {...rest}
      >
        {loading ? <Spinner size={size === 'sm' ? 12 : 14} /> : iconLeft}
        {children}
      </button>
    )
  }
)
Button.displayName = 'Button'
