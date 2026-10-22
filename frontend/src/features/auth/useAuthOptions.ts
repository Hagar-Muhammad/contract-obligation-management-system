import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import { unwrap } from '../../api/errors'

/** Public options for the sign-in pages (e.g. whether self sign-up is enabled). */
export function useAuthOptions() {
  return useQuery({
    queryKey: ['auth', 'options'],
    queryFn: async () => unwrap(await api.GET('/api/v1/auth/options')),
    staleTime: Infinity,
  })
}
