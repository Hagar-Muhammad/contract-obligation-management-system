import { Route, Routes } from 'react-router-dom'
import { PERMISSIONS } from '../auth/context'
import { RequireAuth, RequirePermission } from '../auth/guards'
import { AppLayout } from '../components/AppLayout'
import { LoginPage } from '../features/auth/LoginPage'
import { HomePage } from '../features/home/HomePage'
import { NotFoundPage } from '../features/home/NotFoundPage'
import { UserFormPage } from '../features/users/UserFormPage'
import { UsersPage } from '../features/users/UsersPage'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route index element={<HomePage />} />
        <Route
          path="users"
          element={
            <RequirePermission permission={PERMISSIONS.userManage}>
              <UsersPage />
            </RequirePermission>
          }
        />
        <Route
          path="users/new"
          element={
            <RequirePermission permission={PERMISSIONS.userManage}>
              <UserFormPage />
            </RequirePermission>
          }
        />
        <Route
          path="users/:id"
          element={
            <RequirePermission permission={PERMISSIONS.userManage}>
              <UserFormPage />
            </RequirePermission>
          }
        />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
