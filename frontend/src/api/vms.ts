import { request } from './client'
import type { Paginated, VMResponse, VMCreate, VMActionRequest, VMMetrics } from '../types'

export interface ListVMsParams {
  page?:      number
  page_size?: number
  search?:    string
  status?:    string
  tenant_id?: string
}

export function listVMs(params: ListVMsParams = {}): Promise<Paginated<VMResponse>> {
  const q = new URLSearchParams()
  if (params.page)      q.set('page',      String(params.page))
  if (params.page_size) q.set('page_size', String(params.page_size))
  if (params.search)    q.set('search',    params.search)
  if (params.status)    q.set('status',    params.status)
  if (params.tenant_id) q.set('tenant_id', params.tenant_id)
  const qs = q.toString()
  return request<Paginated<VMResponse>>(`/api/v1/vms${qs ? `?${qs}` : ''}`)
}

export function createVM(body: VMCreate): Promise<VMResponse> {
  return request<VMResponse>('/api/v1/vms', {
    method: 'POST',
    body:   JSON.stringify(body),
  })
}

export function vmAction(id: string, body: VMActionRequest): Promise<VMResponse> {
  return request<VMResponse>(`/api/v1/vms/${id}/actions`, {
    method: 'POST',
    body:   JSON.stringify(body),
  })
}

export function getVMMetrics(id: string): Promise<VMMetrics> {
  return request<VMMetrics>(`/api/v1/vms/${id}/metrics`)
}
