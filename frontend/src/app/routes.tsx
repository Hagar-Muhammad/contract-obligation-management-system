import type { ReactNode } from 'react'
import { Route, Routes } from 'react-router-dom'
import { PERMISSIONS } from '../auth/context'
import { RequireAuth, RequirePermission } from '../auth/guards'
import { AppShell } from '../components/AppShell'
import { UPCOMING_PAGES } from '../components/nav'
import { LoginPage } from '../features/auth/LoginPage'
import { SignUpPage } from '../features/auth/SignUpPage'
import { DashboardPage } from '../features/dashboard/DashboardPage'
import { AuditLogPage } from '../features/audit/AuditLogPage'
import { PartiesPage } from '../features/parties/PartiesPage'
import { PartyFormPage } from '../features/parties/PartyFormPage'
import { ComingSoonPage } from '../features/placeholder/ComingSoonPage'
import { NotFoundPage } from '../features/placeholder/NotFoundPage'
import { PropertiesPage } from '../features/properties/PropertiesPage'
import { PropertyFormPage } from '../features/properties/PropertyFormPage'
import { UserFormPage } from '../features/users/UserFormPage'
import { UsersPage } from '../features/users/UsersPage'

const guarded = (permission: string, page: ReactNode) => (
  <RequirePermission permission={permission}>{page}</RequirePermission>
)
const adminOnly = (page: ReactNode) => guarded(PERMISSIONS.userManage, page)

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
        <Route path="audit-log" element={guarded(PERMISSIONS.auditView, <AuditLogPage />)} />
        <Route path="parties" element={guarded(PERMISSIONS.contractView, <PartiesPage />)} />
        <Route path="parties/new" element={guarded(PERMISSIONS.partyManage, <PartyFormPage />)} />
        <Route path="parties/:id" element={guarded(PERMISSIONS.contractView, <PartyFormPage />)} />
        <Route path="properties" element={guarded(PERMISSIONS.contractView, <PropertiesPage />)} />
        <Route path="properties/new" element={guarded(PERMISSIONS.propertyManage, <PropertyFormPage />)} />
        <Route path="properties/:id" element={guarded(PERMISSIONS.contractView, <PropertyFormPage />)} />
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
