import { useState, useCallback, useRef, useEffect } from 'react'
import { FixedSizeList, type ListChildComponentProps } from 'react-window'
import { Search, RefreshCw } from 'lucide-react'
import type { VMResponse } from '../../types'
import { VMRow } from './VMRow'
import { TableSkeleton } from '../ui/Skeleton'

const COL_HEADER = 'text-[10px] font-semibold uppercase tracking-[0.8px] text-slate-500 dark:text-gray-400 px-2 py-2'

interface VMTableProps {
  vms:         VMResponse[]
  isLoading:   boolean
  onAction:    (action: string, vm: VMResponse) => void
  onRefresh:   () => void
}

const ROW_HEIGHT = 44

export function VMTable({ vms, isLoading, onAction, onRefresh }: VMTableProps) {
  const [search,   setSearch]   = useState('')
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const containerRef = useRef<HTMLDivElement>(null)
  const [listHeight, setListHeight] = useState(400)

  /* Resize observer for the list container */
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const obs = new ResizeObserver(entries => {
      setListHeight(entries[0].contentRect.height)
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  const filtered = vms.filter(vm =>
    vm.name.toLowerCase().includes(search.toLowerCase()) ||
    vm.status.toLowerCase().includes(search.toLowerCase()) ||
    (vm.os_variant ?? '').toLowerCase().includes(search.toLowerCase())
  )

  const toggleSelect = useCallback((id: string, val: boolean) => {
    setSelected(prev => {
      const next = new Set(prev)
      val ? next.add(id) : next.delete(id)
      return next
    })
  }, [])

  const toggleAll = (checked: boolean) => {
    setSelected(checked ? new Set(filtered.map(v => v.id)) : new Set())
  }

  const Row = ({ index, style }: ListChildComponentProps<VMResponse[]>) => (
    <VMRow
      vm={filtered[index]}
      style={style}
      selected={selected.has(filtered[index].id)}
      onSelect={toggleSelect}
      onAction={onAction}
    />
  )

  return (
    <div className="flex flex-col bg-white dark:bg-dark-surface border border-black/[0.07] dark:border-white/[0.07] rounded-xl overflow-hidden h-full">
      {/* Panel header */}
      <div className="flex items-center gap-2.5 px-4 py-3 border-b border-black/[0.06] dark:border-white/[0.07] shrink-0">
        <span className="font-display text-[14px] font-semibold text-slate-900 dark:text-gray-100">All VMs</span>
        <span className="font-mono text-[11px] text-slate-400 dark:text-gray-500 bg-slate-100 dark:bg-dark-bg3 px-2 py-0.5 rounded-full">
          {filtered.length}
        </span>
        <div className="ml-auto flex items-center gap-2">
          <div className="relative">
            <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 dark:text-gray-500 pointer-events-none" />
            <input
              type="text"
              placeholder="Search VMs…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-7 pr-3 py-1.5 rounded-md text-[12px] w-44 bg-slate-100 dark:bg-dark-bg3 border border-black/[0.06] dark:border-white/[0.06] text-slate-900 dark:text-gray-100 placeholder:text-slate-400 dark:placeholder:text-gray-600 focus:outline-none focus:border-accent"
            />
          </div>
          <button
            onClick={onRefresh}
            className="p-1.5 text-slate-400 dark:text-gray-500 hover:text-slate-700 dark:hover:text-gray-200 hover:bg-slate-100 dark:hover:bg-dark-bg3 rounded transition-colors"
            title="Refresh"
          >
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      {/* Header row */}
      <div className="grid grid-cols-[36px_2fr_1fr_56px_72px_80px_80px_100px_44px] shrink-0 bg-slate-50 dark:bg-dark-bg3 border-b border-black/[0.05] dark:border-white/[0.05]">
        <div className="px-3 py-2">
          <input
            type="checkbox"
            onChange={e => toggleAll(e.target.checked)}
            checked={selected.size === filtered.length && filtered.length > 0}
            className="accent-accent w-3.5 h-3.5"
          />
        </div>
        {['Name', 'Status', 'vCPU', 'RAM', 'CPU%', 'Disk', 'Last Backup', ''].map(h => (
          <div key={h} className={COL_HEADER}>{h}</div>
        ))}
      </div>

      {/* Body */}
      <div ref={containerRef} className="flex-1 min-h-0">
        {isLoading ? (
          <TableSkeleton rows={8} cols={9} />
        ) : filtered.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-[13px] text-slate-400 dark:text-gray-500">
            {search ? 'No VMs match your search' : 'No virtual machines'}
          </div>
        ) : (
          <FixedSizeList
            height={listHeight}
            itemCount={filtered.length}
            itemSize={ROW_HEIGHT}
            width="100%"
            itemData={filtered}
          >
            {Row}
          </FixedSizeList>
        )}
      </div>
    </div>
  )
}
