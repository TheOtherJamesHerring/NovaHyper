import { request, downloadFile } from './client'
import type { Paginated, AuditEvent } from '../types'

export interface ListAuditParams {
  page?:          number
  page_size?:     number
  action?:        string
  resource_type?: string
  resource_id?:   string
  user_id?:       string
  from_ts?:       string
  to_ts?:         string
  tenant_id?:     string
}

export function listAudit(params: ListAuditParams = {}): Promise<Paginated<AuditEvent>> {
  const q = new URLSearchParams()
  if (params.page)          q.set('page',          String(params.page))
  if (params.page_size)     q.set('page_size',      String(params.page_size))
  if (params.action)        q.set('action',         params.action)
  if (params.resource_type) q.set('resource_type',  params.resource_type)
  if (params.resource_id)   q.set('resource_id',    params.resource_id)
  if (params.user_id)       q.set('user_id',        params.user_id)
  if (params.from_ts)       q.set('from_ts',        params.from_ts)
  if (params.to_ts)         q.set('to_ts',          params.to_ts)
  const qs = q.toString()
  return request<Paginated<AuditEvent>>(`/api/v1/audit${qs ? `?${qs}` : ''}`)
}

export function getAuditEvent(id: string): Promise<AuditEvent> {
  return request<AuditEvent>(`/api/v1/audit/${id}`)
}

export function exportAuditCSV(params: ListAuditParams = {}): Promise<void> {
  const q = new URLSearchParams()
  if (params.tenant_id) q.set('tenant_id', params.tenant_id)
  if (params.from_ts)   q.set('from_ts',   params.from_ts)
  if (params.to_ts)     q.set('to_ts',     params.to_ts)
  const qs = q.toString()
  return downloadFile(
    `/api/v1/audit/export${qs ? `?${qs}` : ''}`,
    `audit-export-${new Date().toISOString().slice(0, 10)}.csv`
  )
}
