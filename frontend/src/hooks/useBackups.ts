import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listBackups, createBackup, cancelBackup } from '../api/backups'
import type { ListBackupsParams } from '../api/backups'

interface UseBackupsOptions {
  refetchInterval?: number
}

export function useBackups(params: ListBackupsParams = {}, options: UseBackupsOptions = {}) {
  return useQuery({
    queryKey: ['backups', params],
    queryFn:  () => listBackups(params),
    staleTime: 5_000,
    refetchInterval: options.refetchInterval ?? (params.status === 'running' ? 5_000 : undefined),
  })
}

export function useCreateBackup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ vm_id, job_type }: { vm_id: string; job_type?: 'full' | 'incremental' }) =>
      createBackup(vm_id, job_type ?? 'incremental'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['backups'] }),
  })
}

export function useCancelBackup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => cancelBackup(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['backups'] }),
  })
}
