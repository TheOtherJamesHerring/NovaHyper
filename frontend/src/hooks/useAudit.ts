import { useQuery } from '@tanstack/react-query'
import { listAudit } from '../api/audit'
import type { ListAuditParams } from '../api/audit'

export function useAudit(params: ListAuditParams = {}) {
  return useQuery({
    queryKey: ['audit', params],
    queryFn:  () => listAudit(params),
    staleTime: 60_000,
  })
}
