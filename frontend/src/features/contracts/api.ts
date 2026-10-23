import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import { unwrap } from '../../api/errors'
import type { components } from '../../api/schema'

export type Contract = components['schemas']['ContractRead']
export type ContractCreate = components['schemas']['ContractCreate']
export type ContractUpdate = components['schemas']['ContractUpdate']
export type ContractView = components['schemas']['ContractView']
export type ContractSort = components['schemas']['ContractSort']
export type ContractCounts = components['schemas']['ContractCounts']
export type Lookup = components['schemas']['LookupRead']
export type ContractStatus = components['schemas']['ContractStatusRead']
export type StatusCode = components['schemas']['StatusCode']
export type PartyRole = components['schemas']['PartyRole']
export type Activity = components['schemas']['ActivityRead']

export const PARTY_ROLES: PartyRole[] = [
  'landlord',
  'tenant',
  'seller',
  'buyer',
  'owner',
  'service_provider',
  'contractor',
  'consultant',
  'partner',
  'licensor',
  'licensee',
  'other',
]

export interface ContractListParams {
  page: number
  pageSize: number
  view?: ContractView
  q?: string
  typeCode?: string
  partyId?: string
  propertyId?: string
  termFrom?: string
  termTo?: string
  sort?: ContractSort
}

const keys = {
  all: ['contracts'] as const,
  list: (params: ContractListParams) => ['contracts', 'list', params] as const,
  counts: ['contracts', 'counts'] as const,
  detail: (id: string) => ['contracts', 'detail', id] as const,
  activity: (id: string) => ['contracts', 'activity', id] as const,
  defaults: ['contracts', 'defaults'] as const,
  types: ['contract-types'] as const,
  statuses: ['contract-statuses'] as const,
}

export function useContracts(params: ContractListParams) {
  return useQuery({
    queryKey: keys.list(params),
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/contracts', {
          params: {
            query: {
              page: params.page,
              page_size: params.pageSize,
              view: params.view,
              q: params.q || undefined,
              type_code: params.typeCode,
              party_id: params.partyId,
              property_id: params.propertyId,
              term_from: params.termFrom,
              term_to: params.termTo,
              sort: params.sort,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  })
}

export function useContractCounts() {
  return useQuery({
    queryKey: keys.counts,
    queryFn: async () => unwrap(await api.GET('/api/v1/contracts/counts')),
  })
}

export function useContract(id: string | undefined) {
  return useQuery({
    queryKey: keys.detail(id ?? ''),
    queryFn: async () =>
      unwrap(await api.GET('/api/v1/contracts/{contract_id}', { params: { path: { contract_id: id! } } })),
    enabled: Boolean(id),
  })
}

export function useContractActivity(id: string) {
  return useQuery({
    queryKey: keys.activity(id),
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/contracts/{contract_id}/activity', { params: { path: { contract_id: id } } }),
      ),
  })
}

export function useContractDefaults(enabled = true) {
  return useQuery({
    queryKey: keys.defaults,
    queryFn: async () => unwrap(await api.GET('/api/v1/contracts/defaults')),
    enabled,
  })
}

export function useContractTypes() {
  return useQuery({
    queryKey: keys.types,
    queryFn: async () => unwrap(await api.GET('/api/v1/contract-types')),
    staleTime: Infinity,
  })
}

export function useContractStatuses() {
  return useQuery({
    queryKey: keys.statuses,
    queryFn: async () => unwrap(await api.GET('/api/v1/contract-statuses')),
    staleTime: Infinity,
  })
}

export function useCreateContract() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: ContractCreate) => unwrap(await api.POST('/api/v1/contracts', { body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.all }),
  })
}

export function useUpdateContract(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: ContractUpdate) =>
      unwrap(
        await api.PATCH('/api/v1/contracts/{contract_id}', { params: { path: { contract_id: id } }, body }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.all }),
  })
}

export function useSetArchived(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (archived: boolean) => {
      const options = { params: { path: { contract_id: id } } }
      return unwrap(
        archived
          ? await api.POST('/api/v1/contracts/{contract_id}/archive', options)
          : await api.POST('/api/v1/contracts/{contract_id}/restore', options),
      )
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.all }),
  })
}
