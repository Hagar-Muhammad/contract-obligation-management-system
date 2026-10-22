import type { ReactNode } from 'react'
import { Route, Routes } from 'react-router-dom'
import { PERMISSIONS } from '../auth/context'
import { RequireAuth, RequirePermission } from '../auth/guards'
import { AppShell } from '../components/AppShell'
import { UPCOMING_PAGES } from '../components/nav'
import { LoginPage } from '../features/auth/LoginPage'
import { SignUpPage } from '../features/auth/SignUpPage'
import { DashboardPage } from '../features/dashboard/DashboardPage'
import { ComingSoonPage } from '../features/placeholder/ComingSoonPage'
import { NotFoundPage } from '../features/placeholder/NotFoundPage'
import { UserFormPage } from '../features/users/UserFormPage'
import { UsersPage } from '../features/users/UsersPage'

const adminOnly = (page: ReactNode) => (
  <RequirePermission permission={PERMISSIONS.userManage}>{page}</RequirePermission>
)

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignUpPage />} />
      <Route
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="users" element={adminOnly(<UsersPage />)} />
        <Route path="users/new" element={adminOnly(<UserFormPage />)} />
        <Route path="users/:id" element={adminOnly(<UserFormPage />)} />
        {UPCOMING_PAGES.map((page) => (
          <Route
            key={page.path}
            path={page.path.slice(1)}
            element={
              <RequirePermission permission={page.permission ?? ''}>
                <ComingSoonPage labelKey={page.labelKey} module={page.module ?? 0} />
              </RequirePermission>
            }
          />
        ))}
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
