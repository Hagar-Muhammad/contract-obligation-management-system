import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import { unwrap } from '../../api/errors'
import type { components } from '../../api/schema'

export type Party = components['schemas']['PartyRead']
export type PartyCreate = components['schemas']['PartyCreate']
export type PartyUpdate = components['schemas']['PartyUpdate']
export type PartyType = components['schemas']['PartyType']

export interface PartyListParams {
  page: number
  pageSize: number
  q?: string
  partyType?: PartyType
}

const keys = {
  all: ['parties'] as const,
  list: (params: PartyListParams) => ['parties', 'list', params] as const,
  detail: (id: string) => ['parties', 'detail', id] as const,
}

export function useParties(params: PartyListParams) {
  return useQuery({
    queryKey: keys.list(params),
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/parties', {
          params: {
            query: {
              page: params.page,
              page_size: params.pageSize,
              q: params.q || undefined,
              party_type: params.partyType,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  })
}

export function useParty(id: string | undefined) {
  return useQuery({
    queryKey: keys.detail(id ?? ''),
    queryFn: async () =>
      unwrap(await api.GET('/api/v1/parties/{party_id}', { params: { path: { party_id: id! } } })),
    enabled: Boolean(id),
  })
}

export function useCreateParty() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: PartyCreate) => unwrap(await api.POST('/api/v1/parties', { body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.all }),
  })
}

export function useUpdateParty(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: PartyUpdate) =>
      unwrap(await api.PATCH('/api/v1/parties/{party_id}', { params: { path: { party_id: id } }, body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.all }),
  })
}
