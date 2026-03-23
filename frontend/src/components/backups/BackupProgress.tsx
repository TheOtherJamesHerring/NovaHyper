import { clsx } from 'clsx'

interface BackupProgressProps {
  value: number
}

export function BackupProgress({ value }: BackupProgressProps) {
  const pct = Math.max(0, Math.min(100, value))
  return (
    <div className="mt-1.5">
      <div className="h-1.5 rounded-full bg-slate-200 dark:bg-dark-bg3 overflow-hidden">
        <div
          className={clsx(
            'h-full rounded-full transition-[width] duration-300',
            pct > 90 ? 'bg-nova-warn' : 'bg-accent'
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="text-[10px] text-slate-500 dark:text-gray-400 mt-0.5 font-mono">{pct}%</div>
    </div>
  )
}
