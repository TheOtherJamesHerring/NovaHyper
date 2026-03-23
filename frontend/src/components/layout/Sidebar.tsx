import { NavLink, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  Monitor,
  Shield,
  Server,
  Building2,
  LayoutDashboard,
  HardDrive,
  Clock,
  BarChart3,
  Users,
  FileText,
  Settings,
} from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'

interface NavItemDef {
  label:   string
  to:      string
  icon:    React.ReactNode
  badge?:  string
  badgeVariant?: 'default' | 'warn' | 'danger'
  mspOnly?: boolean
}

const SECTIONS: { heading: string; items: NavItemDef[] }[] = [
  {
    heading: 'Compute',
    items: [
      { label: 'Dashboard',        to: '/',    icon: <LayoutDashboard size={14} /> },
      { label: 'Virtual Machines', to: '/vms', icon: <Monitor         size={14} /> },
    ],
  },
  {
    heading: 'Data Protection',
    items: [
      { label: 'Backups', to: '/backups', icon: <Shield    size={14} /> },
    ],
  },
  {
    heading: 'Infrastructure',
    items: [
      { label: 'KVM Hosts', to: '/hosts',   icon: <Server    size={14} />, badge: 'Soon' },
      { label: 'Storage',   to: '/storage', icon: <HardDrive size={14} />, badge: 'Soon' },
    ],
  },
  {
    heading: 'MSP Admin',
    items: [
      { label: 'Tenants',    to: '/tenants',  icon: <Building2 size={14} />, mspOnly: true },
      { label: 'Usage',      to: '/usage',    icon: <BarChart3 size={14} />, badge: 'Soon', mspOnly: true },
      { label: 'Audit Log',  to: '/audit',    icon: <FileText  size={14} /> },
      { label: 'Users',      to: '/users',    icon: <Users     size={14} />, badge: 'Soon' },
      { label: 'Schedules',  to: '/schedules',icon: <Clock     size={14} />, badge: 'Soon' },
      { label: 'Settings',   to: '/settings', icon: <Settings  size={14} /> },
    ],
  },
]

export function Sidebar() {
  const { isMspAdmin } = useAuth()
  const location = useLocation()

  return (
    <nav className="w-[220px] shrink-0 bg-white dark:bg-dark-bg2 border-r border-black/[0.06] dark:border-white/[0.07] flex flex-col py-4 overflow-y-auto">
      {SECTIONS.map(section => {
        const visibleItems = section.items.filter(item => !item.mspOnly || isMspAdmin)
        if (visibleItems.length === 0) return null
        return (
          <div key={section.heading} className="mb-5">
            <div className="px-4 mb-1.5 text-[10px] font-semibold uppercase tracking-[1.2px] text-slate-400 dark:text-gray-500">
              {section.heading}
            </div>
            {visibleItems.map(item => (
              <NavItem
                key={item.to}
                item={item}
                active={
                  item.to === '/'
                    ? location.pathname === '/'
                    : location.pathname.startsWith(item.to)
                }
              />
            ))}
          </div>
        )
      })}
    </nav>
  )
}

function NavItem({ item, active }: { item: NavItemDef; active: boolean }) {
  return (
    <NavLink
      to={item.to}
      end={item.to === '/'}
      className={clsx(
        'flex items-center gap-2.5 px-4 py-2 text-[13px] transition-colors',
        'border-l-2 cursor-pointer',
        active
          ? 'border-accent text-accent bg-slate-50 dark:bg-dark-bg3'
          : 'border-transparent text-slate-500 dark:text-gray-400 hover:text-slate-800 dark:hover:text-gray-200 hover:bg-slate-50 dark:hover:bg-dark-bg3'
      )}
    >
      <span className="shrink-0">{item.icon}</span>
      <span className="flex-1 truncate">{item.label}</span>
      {item.badge && (
        <span
          className={clsx(
            'text-[10px] font-mono px-1.5 py-0.5 rounded-full',
            item.badgeVariant === 'danger'
              ? 'bg-nova-danger text-white'
              : item.badgeVariant === 'warn'
              ? 'bg-nova-warn text-white'
              : 'bg-accent text-white'
          )}
        >
          {item.badge}
        </span>
      )}
    </NavLink>
  )
}
