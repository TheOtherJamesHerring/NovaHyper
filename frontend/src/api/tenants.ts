import { request } from './client'
import type { Paginated, TenantResponse, TenantDetailResponse, TenantCreate, UserResponse } from '../types'

export function listTenants(page = 1, page_size = 25): Promise<Paginated<TenantResponse>> {
  return request<Paginated<TenantResponse>>(
    `/api/v1/tenants?page=${page}&page_size=${page_size}`
  )
}

export function createTenant(body: TenantCreate): Promise<TenantResponse> {
  return request<TenantResponse>('/api/v1/tenants', {
    method: 'POST',
    body:   JSON.stringify(body),
  })
}

export function getTenantDetail(id: string): Promise<TenantDetailResponse> {
  return request<TenantDetailResponse>(`/api/v1/tenants/${id}`)
}

/**
 * Optional endpoint: may not exist in all backend builds yet.
 * Returns null when unavailable (404/405), allowing graceful UI fallback.
 */
export async function listTenantUsers(id: string): Promise<UserResponse[] | null> {
  try {
    const res = await request<Paginated<UserResponse> | UserResponse[]>(`/api/v1/tenants/${id}/users`)
    return Array.isArray(res) ? res : res.items
  } catch (err) {
    const msg = err instanceof Error ? err.message : ''
    if (msg.includes('404') || msg.includes('405')) return null
    throw err
  }
}

export function suspendTenant(id: string, reason = 'Suspended by MSP admin'): Promise<TenantResponse> {
  return request<TenantResponse>(`/api/v1/tenants/${id}/suspend`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })
}

export function reinstateTenant(id: string, reason = 'Reinstated by MSP admin'): Promise<TenantResponse> {
  return request<TenantResponse>(`/api/v1/tenants/${id}/reinstate`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })
}
