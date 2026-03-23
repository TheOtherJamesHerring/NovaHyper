import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listTenants, createTenant, suspendTenant, reinstateTenant } from '../api/tenants'
import type { TenantCreate } from '../types'

export function useTenants(page = 1, pageSize = 25) {
  return useQuery({
    queryKey: ['tenants', page, pageSize],
    queryFn:  () => listTenants(page, pageSize),
    staleTime: 30_000,
  })
}

export function useCreateTenant() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: TenantCreate) => createTenant(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tenants'] }),
  })
}

export function useSuspendTenant() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) => suspendTenant(id, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tenants'] }),
  })
}

export function useReinstateTenant() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) => reinstateTenant(id, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tenants'] }),
  })
}
