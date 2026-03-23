import type { ReactNode } from 'react'

interface PageHeaderProps {
  title:       string
  subtitle?:   string
  actions?:    ReactNode
}

export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <div className="flex items-end gap-4 px-6 pt-5 pb-0 flex-wrap">
      <div>
        <h1 className="font-display text-[20px] font-semibold text-slate-900 dark:text-gray-100">
          {title}
        </h1>
        {subtitle && (
          <p className="text-[12px] text-slate-500 dark:text-gray-400 mt-0.5">{subtitle}</p>
        )}
      </div>
      {actions && <div className="ml-auto flex gap-2">{actions}</div>}
    </div>
  )
}
