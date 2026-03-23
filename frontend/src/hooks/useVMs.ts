import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listVMs, createVM, vmAction } from '../api/vms'
import type { ListVMsParams } from '../api/vms'
import type { VMCreate, VMActionRequest, VMResponse } from '../types'

interface UseVMsOptions {
  refetchInterval?: number
}

export function useVMs(params: ListVMsParams = {}, options: UseVMsOptions = {}) {
  return useQuery({
    queryKey: ['vms', params],
    queryFn:  () => listVMs(params),
    staleTime: 30_000,
    refetchInterval: options.refetchInterval,
  })
}

export function useCreateVM() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: VMCreate) => createVM(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['vms'] })
    },
  })
}

export function useVMAction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: VMActionRequest }) => vmAction(id, body),
    onMutate: async ({ id, body }) => {
      const key = ['vms']
      await qc.cancelQueries({ queryKey: key })
      const snapshots = qc.getQueriesData<{ items: VMResponse[] }>({ queryKey: key })
      snapshots.forEach(([k, data]) => {
        if (!data) return
        const nextStatus = body.action === 'start'
          ? 'running'
          : body.action === 'stop'
          ? 'stopped'
          : body.action === 'pause'
          ? 'paused'
          : data.items.find(vm => vm.id === id)?.status ?? 'running'

        qc.setQueryData(k, {
          ...data,
          items: data.items.map(vm => vm.id === id ? { ...vm, status: nextStatus as VMResponse['status'] } : vm),
        })
      })
      return { snapshots }
    },
    onError: (_err, _vars, ctx) => {
      ctx?.snapshots?.forEach(([k, data]) => qc.setQueryData(k, data))
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['vms'] })
    },
  })
}
