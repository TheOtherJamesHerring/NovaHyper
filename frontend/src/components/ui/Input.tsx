import { type InputHTMLAttributes, forwardRef } from 'react'
import { clsx } from 'clsx'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?:   string
  error?:   string
  startIcon?:  React.ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, startIcon, className, id, ...rest }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-')
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-gray-400"
          >
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          {startIcon && (
            <span className="absolute left-2.5 text-slate-400 dark:text-gray-500 select-none">
              {startIcon}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            className={clsx(
              'w-full rounded-md text-[13px] transition-colors outline-none',
              'bg-slate-100 dark:bg-dark-bg3',
              'border border-black/[0.08] dark:border-white/[0.07]',
              'text-slate-900 dark:text-gray-100',
              'placeholder:text-slate-400 dark:placeholder:text-gray-600',
              'focus:border-accent',
              'disabled:opacity-60 disabled:cursor-not-allowed',
              startIcon ? 'pl-8 pr-3 py-2' : 'px-3 py-2',
              error && 'border-nova-danger focus:border-nova-danger',
              className
            )}
            {...rest}
          />
        </div>
        {error && <p className="text-[11px] text-nova-danger">{error}</p>}
      </div>
    )
  }
)
Input.displayName = 'Input'
