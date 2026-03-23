import {
  useState,
  useRef,
  useCallback,
  useLayoutEffect,
  type ReactNode,
  type CSSProperties,
} from 'react'
import { createPortal } from 'react-dom'
import { clsx } from 'clsx'

type Placement = 'top' | 'bottom' | 'left' | 'right'

interface PopoverProps {
  trigger:    ReactNode
  content:    ReactNode
  delay?:     number
  placement?: Placement
  className?: string
  onOpenChange?: (open: boolean) => void
}

interface Pos { top: number; left: number; transform: string }

export function Popover({
  trigger,
  content,
  delay = 200,
  placement = 'bottom',
  className,
  onOpenChange,
}: PopoverProps) {
  const [visible, setVisible]   = useState(false)
  const [pos, setPos]           = useState<Pos>({ top: 0, left: 0, transform: '' })
  const triggerRef = useRef<HTMLSpanElement>(null)
  const popoverRef = useRef<HTMLDivElement>(null)
  const showTimer  = useRef<ReturnType<typeof setTimeout> | null>(null)
  const hideTimer  = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearTimers = () => {
    if (showTimer.current) clearTimeout(showTimer.current)
    if (hideTimer.current) clearTimeout(hideTimer.current)
  }

  const calculatePos = useCallback((): Pos => {
    if (!triggerRef.current) return { top: 0, left: 0, transform: '' }
    const r   = triggerRef.current.getBoundingClientRect()
    const vw  = window.innerWidth
    const vh  = window.innerHeight
    const gap = 8

    // Default: bottom-center
    let p: Placement = placement
    if (placement === 'bottom' && r.bottom + 200 > vh && r.top > 200) p = 'top'
    if (placement === 'top'    && r.top    < 200         && r.bottom + 200 <= vh) p = 'bottom'

    switch (p) {
      case 'bottom': {
        let left = r.left + r.width / 2
        left = Math.max(8, Math.min(left, vw - 8))
        return { top: r.bottom + gap, left, transform: 'translateX(-50%)' }
      }
      case 'top': {
        let left = r.left + r.width / 2
        left = Math.max(8, Math.min(left, vw - 8))
        return { top: r.top - gap, left, transform: 'translate(-50%, -100%)' }
      }
      case 'left':
        return { top: r.top + r.height / 2, left: r.left - gap, transform: 'translate(-100%, -50%)' }
      case 'right':
        return { top: r.top + r.height / 2, left: r.right + gap, transform: 'translateY(-50%)' }
    }
  }, [placement])

  const show = useCallback(() => {
    setPos(calculatePos())
    setVisible(true)
    onOpenChange?.(true)
  }, [calculatePos, onOpenChange])

  const hide = useCallback(() => {
    setVisible(false)
    onOpenChange?.(false)
  }, [onOpenChange])

  const handleTriggerEnter = useCallback(() => {
    clearTimers()
    showTimer.current = setTimeout(show, delay)
  }, [show, delay])

  const handleTriggerLeave = useCallback(() => {
    clearTimers()
    hideTimer.current = setTimeout(hide, 150)
  }, [hide])

  const handlePopoverEnter = useCallback(() => {
    clearTimers()
  }, [])

  const handlePopoverLeave = useCallback(() => {
    clearTimers()
    hideTimer.current = setTimeout(hide, 150)
  }, [hide])

  /* Recalculate on scroll/resize while visible */
  useLayoutEffect(() => {
    if (!visible) return
    const update = () => setPos(calculatePos())
    window.addEventListener('scroll', update, true)
    window.addEventListener('resize', update)
    return () => {
      window.removeEventListener('scroll', update, true)
      window.removeEventListener('resize', update)
    }
  }, [visible, calculatePos])

  const style: CSSProperties = {
    position:  'fixed',
    top:       pos.top,
    left:      pos.left,
    transform: pos.transform,
    zIndex:    9999,
  }

  return (
    <>
      <span
        ref={triggerRef}
        onMouseEnter={handleTriggerEnter}
        onMouseLeave={handleTriggerLeave}
        style={{ display: 'inline-block' }}
      >
        {trigger}
      </span>

      {visible &&
        createPortal(
          <div
            ref={popoverRef}
            style={style}
            onMouseEnter={handlePopoverEnter}
            onMouseLeave={handlePopoverLeave}
            className={clsx(
              'rounded-lg shadow-xl border pointer-events-auto',
              'bg-white dark:bg-dark-bg2',
              'border-black/[0.08] dark:border-white/[0.12]',
              'text-slate-900 dark:text-gray-100',
              'animate-[popoverIn_0.12s_ease]',
              className
            )}
          >
            {content}

            <style>{`
              @keyframes popoverIn {
                from { opacity: 0; transform: ${pos.transform} scale(0.95); }
                to   { opacity: 1; transform: ${pos.transform} scale(1); }
              }
            `}</style>
          </div>,
          document.body
        )}
    </>
  )
}
