import { vi } from 'vitest'
import type { Me, TokenResponse } from '../api/client'

export type Handler = (request: Request, params: Record<string, string>) => Response | Promise<Response>

export interface RecordedCall {
  method: string
  path: string
  search: string
  body: unknown
  authorization: string | null
}

export const json = (status: number, body?: unknown): Response =>
  new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

export const apiError = (status: number, code: string, message: string, details?: unknown) =>
  json(status, { error: { code, message, ...(details === undefined ? {} : { details }) } })

/**
 * Replace global fetch with a router: keys are "METHOD /path/:param".
 * Unmatched requests return 404 so a missing mock is visible in the test.
 */
export function mockApi(routes: Record<string, Handler>) {
  const compiled = Object.entries(routes).map(([key, handler]) => {
    const [method, pattern] = key.split(' ')
    const names: string[] = []
    const regex = new RegExp(
      '^' +
        pattern.replace(/:([a-z_]+)/gi, (_, name: string) => {
          names.push(name)
          return '([^/]+)'
        }) +
        '$',
    )
    return { method, regex, names, handler }
  })
  const calls: RecordedCall[] = []

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = input instanceof Request ? input : new Request(String(input), init)
    const url = new URL(request.url)
    const text = request.method === 'GET' ? '' : await request.clone().text()
    const isJson = request.headers.get('Content-Type')?.includes('json') ?? false
    calls.push({
      method: request.method,
      path: url.pathname,
      search: url.search,
      // JSON bodies are parsed; others (e.g. multipart uploads) are kept as text.
      body: text ? (isJson ? JSON.parse(text) : text) : undefined,
      authorization: request.headers.get('Authorization'),
    })
    for (const route of compiled) {
      const match = route.method === request.method ? route.regex.exec(url.pathname) : null
      if (match) {
        const params = Object.fromEntries(route.names.map((name, i) => [name, match[i + 1]]))
        return route.handler(request, params)
      }
    }
    return apiError(404, 'not_found', `No mock for ${request.method} ${url.pathname}`)
  })

  vi.stubGlobal('fetch', fetchMock)
  return {
    calls,
    fetchMock,
    callsTo: (method: string, path: string) => calls.filter((c) => c.method === method && c.path === path),
  }
}

const ALL_PERMISSIONS = [
  'audit:view',
  'contract:archive',
  'contract:create',
  'contract:edit',
  'contract:view',
  'document:upload',
  'document:view',
  'extraction:confirm',
  'extraction:run',
  'obligation:create',
  'obligation:update',
  'obligation:view',
  'party:manage',
  'property:manage',
  'report:export',
  'report:view',
  'role:manage',
  'user:manage',
]

export const ADMIN: Me = {
  id: '11111111-1111-1111-1111-111111111111',
  email: 'admin@example.com',
  full_name: 'Ada Admin',
  preferred_language: 'en',
  roles: ['admin'],
  permissions: ALL_PERMISSIONS,
  data_scopes: ['all'],
}

export const EMPLOYEE: Me = {
  id: '22222222-2222-2222-2222-222222222222',
  email: 'emp@example.com',
  full_name: 'Eve Employee',
  preferred_language: 'en',
  roles: ['employee'],
  // Same as the seeded Employee role (backend/app/modules/users/rbac.py).
  permissions: [
    'contract:view',
    'document:upload',
    'document:view',
    'extraction:run',
    'obligation:create',
    'obligation:update',
    'obligation:view',
    'report:view',
  ],
  data_scopes: ['assigned_obligations'],
}

export const tokenFor = (user: Me, token = `token-${user.id}`): TokenResponse => ({
  access_token: token,
  token_type: 'bearer',
  expires_in: 900,
  user,
})

/** Routes for an already-logged-in user: the refresh cookie restores the session on load. */
export const signedInAs = (user: Me): Record<string, Handler> => ({
  'POST /api/v1/auth/refresh': () => json(200, tokenFor(user)),
  'POST /api/v1/auth/logout': () => new Response(null, { status: 204 }),
})

export const signedOut: Record<string, Handler> = {
  'POST /api/v1/auth/refresh': () => apiError(401, 'unauthorized', 'No refresh token.'),
}
