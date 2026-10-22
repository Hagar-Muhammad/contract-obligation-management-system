import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import { unwrap } from '../../api/errors'
import type { components } from '../../api/schema'

export type User = components['schemas']['UserRead']
export type UserCreate = components['schemas']['UserCreate']
export type UserUpdate = components['schemas']['UserUpdate']
export type Role = components['schemas']['RoleRead']
export type RoleCode = UserCreate['role_codes'][number]

export interface UserListParams {
  page: number
  pageSize: number
  q?: string
}

const keys = {
  all: ['users'] as const,
  list: (params: UserListParams) => ['users', 'list', params] as const,
  detail: (id: string) => ['users', 'detail', id] as const,
  roles: ['roles'] as const,
}

export function useUsers(params: UserListParams) {
  return useQuery({
    queryKey: keys.list(params),
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/users', {
          params: { query: { page: params.page, page_size: params.pageSize, q: params.q || undefined } },
        }),
      ),
    placeholderData: keepPreviousData,
  })
}

export function useUser(id: string | undefined) {
  return useQuery({
    queryKey: keys.detail(id ?? ''),
    queryFn: async () =>
      unwrap(await api.GET('/api/v1/users/{user_id}', { params: { path: { user_id: id! } } })),
    enabled: Boolean(id),
  })
}

export function useRoles() {
  return useQuery({
    queryKey: keys.roles,
    queryFn: async () => unwrap(await api.GET('/api/v1/roles')),
    staleTime: Infinity,
  })
}

export function useCreateUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: UserCreate) => unwrap(await api.POST('/api/v1/users', { body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.all }),
  })
}

export function useUpdateUser(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: UserUpdate) =>
      unwrap(await api.PATCH('/api/v1/users/{user_id}', { params: { path: { user_id: id } }, body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.all }),
  })
}

export function useSetUserActive() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, active }: { id: string; active: boolean }) => {
      const options = { params: { path: { user_id: id } } }
      return unwrap(
        active
          ? await api.POST('/api/v1/users/{user_id}/activate', options)
          : await api.POST('/api/v1/users/{user_id}/deactivate', options),
      )
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.all }),
  })
}
