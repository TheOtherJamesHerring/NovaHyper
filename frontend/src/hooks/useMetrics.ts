import { useQuery } from '@tanstack/react-query'
import { getVMMetrics } from '../api/vms'

export function useMetrics(vmId: string | null) {
  return useQuery({
    queryKey: ['metrics', vmId],
    queryFn:  () => getVMMetrics(vmId as string),
    enabled: !!vmId,
    staleTime: 10_000,
    refetchInterval: 10_000,
  })
}
