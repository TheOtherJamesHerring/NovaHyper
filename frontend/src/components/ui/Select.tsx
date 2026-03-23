import { type SelectHTMLAttributes, forwardRef } from 'react'
import { clsx } from 'clsx'

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?:    string
  error?:    string
  options?:  { label: string; value: string }[]
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, options, className, id, children, ...rest }, ref) => {
    const selectId = id ?? label?.toLowerCase().replace(/\s+/g, '-')
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={selectId}
            className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-gray-400"
          >
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          className={clsx(
            'w-full rounded-md text-[13px] transition-colors outline-none',
            'bg-slate-100 dark:bg-dark-bg3',
            'border border-black/[0.08] dark:border-white/[0.07]',
            'text-slate-900 dark:text-gray-100',
            'focus:border-accent',
            'disabled:opacity-60 disabled:cursor-not-allowed',
            'px-3 py-2',
            error && 'border-nova-danger',
            className
          )}
          {...rest}
        >
          {options
            ? options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)
            : children}
        </select>
        {error && <p className="text-[11px] text-nova-danger">{error}</p>}
      </div>
    )
  }
)
Select.displayName = 'Select'
