import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import { unwrap } from '../../api/errors'
import type { components } from '../../api/schema'

export type Property = components['schemas']['PropertyRead']
export type PropertyCreate = components['schemas']['PropertyCreate']
export type PropertyUpdate = components['schemas']['PropertyUpdate']
export type PropertyType = components['schemas']['PropertyType']
export type PropertyManager = components['schemas']['PropertyManagerRead']

export const PROPERTY_TYPES: PropertyType[] = [
  'residential',
  'retail',
  'office',
  'industrial',
  'land',
  'mixed_use',
  'other',
]

export interface PropertyListParams {
  page: number
  pageSize: number
  q?: string
  propertyType?: PropertyType
}

const keys = {
  all: ['properties'] as const,
  list: (params: PropertyListParams) => ['properties', 'list', params] as const,
  detail: (id: string) => ['properties', 'detail', id] as const,
  assignable: (q: string) => ['properties', 'assignable-managers', q] as const,
}

export function useProperties(params: PropertyListParams) {
  return useQuery({
    queryKey: keys.list(params),
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/properties', {
          params: {
            query: {
              page: params.page,
              page_size: params.pageSize,
              q: params.q || undefined,
              property_type: params.propertyType,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  })
}

export function useProperty(id: string | undefined) {
  return useQuery({
    queryKey: keys.detail(id ?? ''),
    queryFn: async () =>
      unwrap(await api.GET('/api/v1/properties/{property_id}', { params: { path: { property_id: id! } } })),
    enabled: Boolean(id),
  })
}

/** Active Property Managers matching `q`; only for users who may assign them. */
export function useAssignableManagers(q: string, enabled: boolean) {
  return useQuery({
    queryKey: keys.assignable(q),
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/properties/assignable-managers', { params: { query: { q: q || undefined } } }),
      ),
    enabled,
    placeholderData: keepPreviousData,
  })
}

export function useCreateProperty() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: PropertyCreate) => unwrap(await api.POST('/api/v1/properties', { body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.all }),
  })
}

export function useUpdateProperty(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: PropertyUpdate) =>
      unwrap(
        await api.PATCH('/api/v1/properties/{property_id}', { params: { path: { property_id: id } }, body }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.all }),
  })
}
