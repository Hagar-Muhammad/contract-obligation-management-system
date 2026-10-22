import createClient from 'openapi-fetch'
import type { components, paths } from './schema'

export type Me = components['schemas']['MeResponse']
export type TokenResponse = components['schemas']['TokenResponse']

export const API_BASE = '/api/v1'

/**
 * The access token lives only in memory (never in localStorage), so injected scripts cannot read it
 * from storage. The refresh token is an httpOnly cookie the browser sends to /api/v1/auth only.
 */
let accessToken: string | null = null
const sessionListeners = new Set<(me: Me | null) => void>()

export function setSession(token: TokenResponse | null): void {
  accessToken = token?.access_token ?? null
  sessionListeners.forEach((listener) => listener(token?.user ?? null))
}

export function onSessionChange(listener: (me: Me | null) => void): () => void {
  sessionListeners.add(listener)
  return () => sessionListeners.delete(listener)
}

let refreshInFlight: Promise<boolean> | null = null

/**
 * Exchange the refresh cookie for a new access token. Concurrent callers share one request:
 * refresh tokens are single-use, so two parallel refreshes would invalidate each other.
 */
export function refreshSession(): Promise<boolean> {
  refreshInFlight ??= (async () => {
    try {
      const response = await globalThis.fetch(`${origin()}${API_BASE}/auth/refresh`, {
        method: 'POST',
        credentials: 'same-origin',
      })
      if (!response.ok) {
        setSession(null)
        return false
      }
      setSession((await response.json()) as TokenResponse)
      return true
    } catch {
      setSession(null)
      return false
    } finally {
      refreshInFlight = null
    }
  })()
  return refreshInFlight
}

const isAuthEndpoint = (url: string) => url.includes(`${API_BASE}/auth/`)

function withToken(request: Request): Request {
  const copy = new Request(request)
  if (accessToken) copy.headers.set('Authorization', `Bearer ${accessToken}`)
  return copy
}

/** Attach the access token; on 401, refresh once and replay the request. */
async function authFetch(request: Request): Promise<Response> {
  const replay = request.clone()
  const response = await globalThis.fetch(withToken(request))
  if (response.status !== 401 || isAuthEndpoint(request.url)) return response
  return (await refreshSession()) ? globalThis.fetch(withToken(replay)) : response
}

function origin(): string {
  return globalThis.location?.origin ?? 'http://localhost'
}

export const api = createClient<paths>({
  baseUrl: origin(),
  credentials: 'same-origin',
  fetch: authFetch,
})
