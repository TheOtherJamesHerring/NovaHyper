import type { SVGProps } from 'react'

/* ── Windows logo — 4-pane flag ─────────────────────────────────────────── */
export function WindowsIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
      <path d="M2 3.5L9.2 2.5V9.5H2V3.5Z"   fill="#0078D4"/>
      <path d="M10.1 2.35L18 1.2V9.5H10.1V2.35Z" fill="#0078D4"/>
      <path d="M2 10.5H9.2V17.5L2 16.5V10.5Z" fill="#0078D4"/>
      <path d="M10.1 10.5H18V18.8L10.1 17.65V10.5Z" fill="#0078D4"/>
    </svg>
  )
}

/* ── Ubuntu — simplified circle of friends ──────────────────────────────── */
export function UbuntuIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
      <circle cx="10" cy="10" r="8" stroke="#E95420" strokeWidth="1.5"/>
      <circle cx="10" cy="3"   r="1.8" fill="#E95420"/>
      <circle cx="3.3" cy="13.5" r="1.8" fill="#E95420"/>
      <circle cx="16.7" cy="13.5" r="1.8" fill="#E95420"/>
      <path d="M10 4.8 A6 6 0 0 0 4.3 12.5" stroke="#E95420" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
      <path d="M10 4.8 A6 6 0 0 1 15.7 12.5" stroke="#E95420" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
      <path d="M4.3 12.5 A6 6 0 0 0 15.7 12.5" stroke="#E95420" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
    </svg>
  )
}

/* ── Debian — swirl ─────────────────────────────────────────────────────── */
export function DebianIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
      <path
        d="M10 2C5.58 2 2 5.58 2 10s3.58 8 8 8 8-3.58 8-8-3.58-8-8-8zm1.6 4.2c1.1.1 2 .5 2.7 1.2-.5-.2-1.1-.3-1.7-.3-1.7 0-3 1-3 2.4 0 1 .8 1.8 2.2 1.8 1.8 0 3.1-1.3 3.1-3.3 0-2.2-1.8-3.8-4-3.8C6.8 4.2 5 6.3 5 9c0 2.8 2.2 5 5 5 2.5 0 4.5-1.6 4.9-3.8-.6 1.4-2 2.3-3.7 2.3-2 0-3.4-1.3-3.4-3.2 0-1.8 1.3-3.1 3.8-3.1z"
        fill="#A80030"
      />
    </svg>
  )
}

/* ── RHEL / AlmaLinux / Rocky — simplified ──────────────────────────────── */
export function RhelIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
      {/* Simplified hat */}
      <ellipse cx="10" cy="14" rx="7" ry="2.5" fill="#CC0000"/>
      <path d="M7 14 Q10 2 13 14Z" fill="#CC0000"/>
      <ellipse cx="10" cy="14" rx="7" ry="2.5" stroke="#9B0000" strokeWidth="0.5"/>
    </svg>
  )
}

/* ── Linux generic — Tux penguin outline ───────────────────────────────── */
export function LinuxIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
      {/* Body */}
      <ellipse cx="10" cy="12.5" rx="5" ry="6" fill="#2c2c2c" stroke="#555" strokeWidth="0.5"/>
      {/* White belly */}
      <ellipse cx="10" cy="13" rx="3" ry="4.5" fill="#f5f5f0"/>
      {/* Head */}
      <ellipse cx="10" cy="6" rx="3.5" ry="3.5" fill="#2c2c2c"/>
      {/* Eyes */}
      <circle cx="8.5" cy="5.3" r="1" fill="white"/>
      <circle cx="11.5" cy="5.3" r="1" fill="white"/>
      <circle cx="8.7" cy="5.4" r="0.5" fill="#222"/>
      <circle cx="11.7" cy="5.4" r="0.5" fill="#222"/>
      {/* Beak */}
      <polygon points="10,7 9.2,8 10.8,8" fill="#F5A623"/>
      {/* Feet */}
      <path d="M7.5 18 Q6.5 19.5 5 19 Q6 17.5 7 17Z" fill="#F5A623"/>
      <path d="M12.5 18 Q13.5 19.5 15 19 Q14 17.5 13 17Z" fill="#F5A623"/>
    </svg>
  )
}

/* ── FreeBSD — daemon head ──────────────────────────────────────────────── */
export function FreeBSDIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
      {/* Horns */}
      <path d="M6 6 Q5 2 7.5 3" stroke="#AB0303" strokeWidth="1.2" fill="none" strokeLinecap="round"/>
      <path d="M14 6 Q15 2 12.5 3" stroke="#AB0303" strokeWidth="1.2" fill="none" strokeLinecap="round"/>
      {/* Face */}
      <ellipse cx="10" cy="11" rx="6.5" ry="7" fill="#AB0303"/>
      {/* Eyes */}
      <circle cx="7.8" cy="9.5" r="1.2" fill="white"/>
      <circle cx="12.2" cy="9.5" r="1.2" fill="white"/>
      <circle cx="8" cy="9.6" r="0.6" fill="#1a1a1a"/>
      <circle cx="12.4" cy="9.6" r="0.6" fill="#1a1a1a"/>
      {/* Tail (bottom arc) */}
      <path d="M5 16 Q10 20 15 16" stroke="#AB0303" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
    </svg>
  )
}

/* ── Custom ISO ─────────────────────────────────────────────────────────── */
export function IsoIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
      <ellipse cx="10" cy="10" rx="8" ry="8" stroke="#6b7280" strokeWidth="1.5" fill="none"/>
      <ellipse cx="10" cy="10" rx="3" ry="3" stroke="#6b7280" strokeWidth="1" fill="none"/>
      <ellipse cx="10" cy="10" rx="1" ry="1" fill="#6b7280"/>
    </svg>
  )
}

/* ── Map: os_type / os_variant → icon ──────────────────────────────────── */
export type OsKey = 'windows' | 'ubuntu' | 'debian' | 'rhel' | 'linux' | 'freebsd' | 'custom'

export function getOsKey(os_type: string, os_variant: string | null | undefined): OsKey {
  const t = os_type.toLowerCase()
  const v = (os_variant ?? '').toLowerCase()
  if (t === 'windows') return 'windows'
  if (t === 'bsd' || v.includes('freebsd')) return 'freebsd'
  if (v.includes('ubuntu'))  return 'ubuntu'
  if (v.includes('debian'))  return 'debian'
  if (v.includes('alma') || v.includes('rocky') || v.includes('rhel') || v.includes('centos') || v.includes('fedora')) return 'rhel'
  if (t === 'linux') return 'linux'
  return 'custom'
}

export const OS_ICON_MAP: Record<OsKey, React.ComponentType<SVGProps<SVGSVGElement>>> = {
  windows: WindowsIcon,
  ubuntu:  UbuntuIcon,
  debian:  DebianIcon,
  rhel:    RhelIcon,
  linux:   LinuxIcon,
  freebsd: FreeBSDIcon,
  custom:  IsoIcon,
}

export const OS_LABEL_MAP: Record<OsKey, string> = {
  windows: 'Windows',
  ubuntu:  'Ubuntu',
  debian:  'Debian',
  rhel:    'AlmaLinux / RHEL',
  linux:   'Linux',
  freebsd: 'FreeBSD',
  custom:  'Custom ISO',
}

export const OS_SUB_MAP: Record<OsKey, string> = {
  windows: 'Server 2022',
  ubuntu:  '22.04 LTS',
  debian:  '12 Bookworm',
  rhel:    'AlmaLinux 9',
  linux:   'Generic',
  freebsd: '14.0',
  custom:  'Upload ISO',
}

interface OsIconProps {
  osType:    string
  osVariant?: string | null
  size?:     number
}

export function OsIcon({ osType, osVariant, size = 20 }: OsIconProps) {
  const key   = getOsKey(osType, osVariant)
  const Icon  = OS_ICON_MAP[key]
  return <Icon width={size} height={size} />
}
