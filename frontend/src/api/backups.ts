import { request } from './client'
import type { Paginated, BackupJobResponse, BackupType, BackupManifest } from '../types'

export interface ListBackupsParams {
  page?:      number
  page_size?: number
  status?:    string
  vm_id?:     string
}

export function listBackups(params: ListBackupsParams = {}): Promise<Paginated<BackupJobResponse>> {
  const q = new URLSearchParams()
  if (params.page)      q.set('page',      String(params.page))
  if (params.page_size) q.set('page_size', String(params.page_size))
  if (params.status)    q.set('status',    params.status)
  if (params.vm_id)     q.set('vm_id',     params.vm_id)
  const qs = q.toString()
  return request<Paginated<BackupJobResponse>>(`/api/v1/backups${qs ? `?${qs}` : ''}`)
}

export function createBackup(vm_id: string, job_type: BackupType = 'incremental'): Promise<BackupJobResponse> {
  return request<BackupJobResponse>('/api/v1/backups', {
    method: 'POST',
    body:   JSON.stringify({ vm_id, job_type }),
  })
}

export function cancelBackup(id: string): Promise<void> {
  return request<void>(`/api/v1/backups/${id}`, { method: 'DELETE' })
}

export function getBackupManifest(id: string): Promise<BackupManifest> {
  return request<BackupManifest>(`/api/v1/backups/${id}/manifest`)
}
