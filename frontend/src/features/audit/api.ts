import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import { unwrap } from '../../api/errors'
import type { components } from '../../api/schema'

export type AuditLog = components['schemas']['AuditLogRead']
export type AuditAction = components['schemas']['AuditAction']

export interface AuditLogParams {
  page: number
  pageSize: number
  q?: string
  action?: AuditAction
  /** ISO timestamps: inclusive lower bound, exclusive upper bound. */
  from?: string
  to?: string
}

export function useAuditLogs(params: AuditLogParams) {
  return useQuery({
    queryKey: ['audit-logs', params],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/audit-logs', {
          params: {
            query: {
              page: params.page,
              page_size: params.pageSize,
              q: params.q || undefined,
              action: params.action,
              occurred_from: params.from,
              occurred_to: params.to,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  })
}
