/* ── Enum mirrors (kept in sync with backend Python enums) ─────────────────── */

export type VMStatus =
  | 'provisioning'
  | 'running'
  | 'stopped'
  | 'paused'
  | 'error'
  | 'deleted'

export type BackupStatus = 'queued' | 'running' | 'success' | 'failed' | 'cancelled'
export type BackupType   = 'full' | 'incremental'
export type DiskFormat   = 'qcow2' | 'raw'
export type StorageType  = 'zfs' | 'ceph_rbd' | 'nfs' | 'lvm'

export type PlanTier     = 'starter' | 'pro' | 'enterprise'
export type TenantStatus = 'active' | 'suspended' | 'cancelled'

export type UserRole =
  | 'msp_admin'
  | 'tenant_admin'
  | 'operator'
  | 'viewer'

/* ── Pagination wrapper ──────────────────────────────────────────────────── */

export interface Paginated<T> {
  items:     T[]
  total:     number
  page:      number
  page_size: number
  has_more:  boolean
}

/* ── Auth ────────────────────────────────────────────────────────────────── */

export interface TokenResponse {
  access_token:  string
  refresh_token: string
  token_type:    string
  expires_in:    number
}

/** Claims decoded from JWT payload */
export interface JwtClaims {
  sub:       string   // user_id
  tenant_id: string
  role:      UserRole
  exp:       number
  iat:       number
  type:      string
}

export interface AuthUser {
  id:        string
  tenant_id: string
  role:      UserRole
}

/* ── Tenants ─────────────────────────────────────────────────────────────── */

export interface TenantResponse {
  id:         string
  name:       string
  slug:       string
  plan_tier:  PlanTier
  status:     TenantStatus
  max_vcpus?: number
  max_ram_gb?: number
  max_storage_gb?: number
  max_backup_gb?: number
  updated_at?: string
  created_at: string
  /* Counts may or may not be present depending on endpoint */
  vm_count?:       number
  user_count?:     number
  storage_used_gb?: number
}

export interface TenantDetailResponse extends TenantResponse {
  max_vcpus: number
  max_ram_gb: number
  max_storage_gb: number
  max_backup_gb: number
  user_count: number
  vm_count: number
  updated_at: string
}

export interface TenantCreate {
  name:             string
  slug:             string
  plan_tier:        PlanTier
  admin_email:      string
  admin_password:   string
  admin_full_name?: string
}

/* ── Users ───────────────────────────────────────────────────────────────── */

export interface UserResponse {
  id:          string
  tenant_id?:  string
  email:       string
  full_name:   string | null
  role:        UserRole
  is_active:   boolean
  created_at:  string
}

/* ── VMs ─────────────────────────────────────────────────────────────────── */

export interface DiskResponse {
  id:             string
  device_name:    string
  path:           string
  size_gb:        number
  disk_format:    DiskFormat
  backup_enabled: boolean
  bitmap_name:    string | null
}

export interface VMResponse {
  id:           string
  name:         string
  description:  string | null
  status:       VMStatus
  vcpus:        number
  ram_mb:       number
  os_type:      string
  os_variant:   string | null
  host_id:      string | null
  libvirt_uuid: string | null
  disks:        DiskResponse[]
  backup_policy: Record<string, unknown>
  tags:          Record<string, string>
  created_at:   string
  updated_at:   string
}

export interface VMCreate {
  name:          string
  description?:  string
  vcpus:         number
  ram_mb:        number
  os_type:       string
  os_variant?:   string
  host_id:       string
  disks: {
    size_gb:         number
    disk_format:     DiskFormat
    storage_pool_id: string
  }[]
  network_id?:    string
  iso_path?:      string
  backup_policy?: Record<string, unknown>
  tags?:          Record<string, string>
}

export interface VMActionRequest {
  action: 'start' | 'stop' | 'reboot' | 'pause' | 'resume' | 'reset'
  force?: boolean
}

export interface VMMetrics {
  cpu_percent:     number
  cpu_5min_avg:    number
  cpu_15min_avg:   number
  mem_used_mb:     number
  mem_total_mb:    number
  disk_read_bytes: number
  disk_write_bytes:number
}

/* ── Backups ─────────────────────────────────────────────────────────────── */

export interface BackupJobResponse {
  id:            string
  vm_id:         string
  job_type:      BackupType
  status:        BackupStatus
  started_at:    string | null
  finished_at:   string | null
  bytes_read:    number
  bytes_written: number
  error_message: string | null
  created_at:    string
}

export interface BackupManifest {
  id:          string
  backup_id:   string
  chunks:      { hash: string; size: number }[]
  created_at:  string
}

/* ── Audit ───────────────────────────────────────────────────────────────── */

export interface AuditEvent {
  id:             string
  tenant_id:      string | null
  user_id:        string | null
  action:         string
  resource_type:  string
  resource_id:    string | null
  integrity_hash: string
  ip_address:     string | null
  user_agent:     string | null
  ts:             string
}

/* ── Notifications (client-side only) ───────────────────────────────────── */

export type NotificationType = 'success' | 'warning' | 'error' | 'info'
export type NotificationSource = 'backup' | 'vm' | 'system'

export interface Notification {
  id:        string
  type:      NotificationType
  title:     string
  message:   string
  timestamp: number
  read:      boolean
  source:    NotificationSource
}
