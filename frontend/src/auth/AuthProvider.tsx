import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, onSessionChange, refreshSession, setSession, type Me } from '../api/client'
import { unwrap } from '../api/errors'
import { AuthContext, type AuthState } from './context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null)
  const [status, setStatus] = useState<AuthState['status']>('loading')

  useEffect(() => {
    const unsubscribe = onSessionChange((me) => {
      setUser(me)
      setStatus(me ? 'authenticated' : 'anonymous')
    })
    // Restore the session from the refresh cookie on page load.
    void refreshSession()
    return unsubscribe
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    setSession(unwrap(await api.POST('/api/v1/auth/login', { body: { email, password } })))
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.POST('/api/v1/auth/logout')
    } finally {
      setSession(null)
    }
  }, [])

  const value = useMemo<AuthState>(
    () => ({
      status,
      user,
      login,
      logout,
      can: (permission: string) => user?.permissions.includes(permission) ?? false,
    }),
    [status, user, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
