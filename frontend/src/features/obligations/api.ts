import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import { unwrap } from '../../api/errors'
import type { components } from '../../api/schema'

export type Obligation = components['schemas']['ObligationRead']
export type ObligationCreate = components['schemas']['ObligationCreate']
export type ObligationUpdate = components['schemas']['ObligationUpdate']
export type ObligationView = components['schemas']['ObligationView']
export type ObligationSort = components['schemas']['ObligationSort']
export type ObligationCounts = components['schemas']['ObligationCounts']
export type Priority = components['schemas']['Priority']
export type ObligationStatus = components['schemas']['ObligationStatus']
export type EffectiveStatus = components['schemas']['EffectiveStatus']
export type UserSummary = components['schemas']['UserSummary']

export const PRIORITIES: Priority[] = ['low', 'medium', 'high', 'critical']
export const STATUSES: ObligationStatus[] = ['pending', 'in_progress', 'completed', 'cancelled']

export interface ObligationListParams {
  page: number
  pageSize: number
  view?: ObligationView
  q?: string
  contractId?: string
  propertyId?: string
  responsibleUserId?: string
  mine?: boolean
  priority?: Priority
  dueFrom?: string
  dueTo?: string
  sort?: ObligationSort
}

const keys = {
  all: ['obligations'] as const,
  list: (params: ObligationListParams) => ['obligations', 'list', params] as const,
  counts: ['obligations', 'counts'] as const,
  detail: (id: string) => ['obligations', 'detail', id] as const,
  activity: (id: string) => ['obligations', 'activity', id] as const,
  evidence: (id: string) => ['obligations', 'evidence', id] as const,
  directory: (q: string) => ['users', 'directory', q] as const,
}

/** Everything that shows obligations or numbers derived from them. */
function invalidateAll(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: keys.all })
  void queryClient.invalidateQueries({ queryKey: ['contracts'] })
}

export function useObligations(params: ObligationListParams, enabled = true) {
  return useQuery({
    queryKey: keys.list(params),
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/obligations', {
          params: {
            query: {
              page: params.page,
              page_size: params.pageSize,
              view: params.view,
              q: params.q || undefined,
              contract_id: params.contractId,
              property_id: params.propertyId,
              responsible_user_id: params.responsibleUserId,
              mine: params.mine || undefined,
              priority: params.priority,
              due_from: params.dueFrom,
              due_to: params.dueTo,
              sort: params.sort,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
    enabled,
  })
}

export function useObligationCounts() {
  return useQuery({
    queryKey: keys.counts,
    queryFn: async () => unwrap(await api.GET('/api/v1/obligations/counts')),
  })
}

export function useObligation(id: string | undefined) {
  return useQuery({
    queryKey: keys.detail(id ?? ''),
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/obligations/{obligation_id}', { params: { path: { obligation_id: id! } } }),
      ),
    enabled: Boolean(id),
  })
}

export function useObligationActivity(id: string) {
  return useQuery({
    queryKey: keys.activity(id),
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/obligations/{obligation_id}/activity', {
          params: { path: { obligation_id: id } },
        }),
      ),
  })
}

export function useObligationEvidence(id: string, enabled: boolean) {
  return useQuery({
    queryKey: keys.evidence(id),
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/obligations/{obligation_id}/evidence', {
          params: { path: { obligation_id: id } },
        }),
      ),
    enabled,
  })
}

export function useUserDirectory(q: string, enabled: boolean) {
  return useQuery({
    queryKey: keys.directory(q),
    queryFn: async () =>
      unwrap(await api.GET('/api/v1/users/directory', { params: { query: { q: q || undefined } } })),
    enabled,
    placeholderData: keepPreviousData,
  })
}

export function useCreateObligation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: ObligationCreate) => unwrap(await api.POST('/api/v1/obligations', { body })),
    onSuccess: () => invalidateAll(queryClient),
  })
}

export function useUpdateObligation(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: ObligationUpdate) =>
      unwrap(
        await api.PATCH('/api/v1/obligations/{obligation_id}', {
          params: { path: { obligation_id: id } },
          body,
        }),
      ),
    onSuccess: () => invalidateAll(queryClient),
  })
}

export function useChangeStatus(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: { status: ObligationStatus; note?: string | null }) =>
      unwrap(
        await api.POST('/api/v1/obligations/{obligation_id}/status', {
          params: { path: { obligation_id: id } },
          body,
        }),
      ),
    onSuccess: () => invalidateAll(queryClient),
  })
}

export function useAddEvidence(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (file: File) =>
      unwrap(
        await api.POST('/api/v1/obligations/{obligation_id}/evidence', {
          params: { path: { obligation_id: id } },
          body: { file: file as unknown as string },
          bodySerializer: (body) => {
            const form = new FormData()
            const chosen = body.file as unknown as File
            form.append('file', chosen, chosen.name)
            return form
          },
        }),
      ),
    onSuccess: () => invalidateAll(queryClient),
  })
}
