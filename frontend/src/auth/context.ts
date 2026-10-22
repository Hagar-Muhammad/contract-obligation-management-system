import { createContext, useContext } from 'react'
import type { Me } from '../api/client'
import type { components } from '../api/schema'

export type SignUpData = components['schemas']['SignUpRequest']

export interface AuthState {
  status: 'loading' | 'authenticated' | 'anonymous'
  user: Me | null
  login: (email: string, password: string) => Promise<void>
  register: (data: SignUpData) => Promise<void>
  logout: () => Promise<void>
  /** UI convenience only; the backend enforces every permission (Appendix B). */
  can: (permission: string) => boolean
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth(): AuthState {
  const auth = useContext(AuthContext)
  if (!auth) throw new Error('useAuth must be used inside <AuthProvider>')
  return auth
}

/** Permission codes, mirroring backend/app/modules/users/rbac.py. */
export const PERMISSIONS = {
  userManage: 'user:manage',
} as const
