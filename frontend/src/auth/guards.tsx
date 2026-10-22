import { Result, Spin } from 'antd'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './context'

/** Routes inside require a logged-in user; others are sent to /login and returned afterwards. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  const location = useLocation()
  if (status === 'loading') {
    return <Spin size="large" fullscreen />
  }
  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  }
  return children
}

export function RequirePermission({ permission, children }: { permission: string; children: ReactNode }) {
  const { can } = useAuth()
  const { t } = useTranslation()
  if (!can(permission)) {
    return <Result status="403" title="403" subTitle={t('errors.forbidden')} />
  }
  return children
}
