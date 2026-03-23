import { clsx } from 'clsx'

interface SkeletonProps {
  className?: string
  lines?:     number
  height?:    number
}

export function Skeleton({ className, height = 16 }: SkeletonProps) {
  return (
    <div
      style={{ height }}
      className={clsx(
        'animate-pulse rounded',
        'bg-slate-200 dark:bg-dark-bg3',
        className
      )}
    />
  )
}

export function SkeletonRow({ cols = 6 }: { cols?: number }) {
  return (
    <div className="flex gap-4 px-3 py-3 border-b border-black/[0.06] dark:border-white/[0.05]">
      {Array.from({ length: cols }).map((_, i) => (
        <Skeleton key={i} className="flex-1" height={14} />
      ))}
    </div>
  )
}

export function TableSkeleton({ rows = 5, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <div>
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonRow key={i} cols={cols} />
      ))}
    </div>
  )
}
