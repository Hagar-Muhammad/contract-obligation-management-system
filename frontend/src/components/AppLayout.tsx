import { Button, Layout, Menu, Space, Typography, type MenuProps } from 'antd'
import { useTranslation } from 'react-i18next'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { PERMISSIONS, useAuth } from '../auth/context'
import { LanguageSwitch } from './LanguageSwitch'
import { Logo } from './Logo'

interface NavItem {
  path: string
  labelKey: string
  permission?: string
}

/** Navigation is filtered by permission so users only see what they can use (NFR-UX-01). */
const NAV_ITEMS: NavItem[] = [
  { path: '/', labelKey: 'nav.home' },
  { path: '/users', labelKey: 'nav.users', permission: PERMISSIONS.userManage },
]

/** Start collapsed on narrow screens so the menu does not flash open before the breakpoint fires. */
const startsCollapsed = () => window.matchMedia?.('(max-width: 767.98px)').matches ?? false

export function AppLayout() {
  const { t } = useTranslation()
  const { user, can, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  const items: MenuProps['items'] = NAV_ITEMS.filter((item) => !item.permission || can(item.permission)).map(
    (item) => ({ key: item.path, label: <Link to={item.path}>{t(item.labelKey)}</Link> }),
  )
  const selected =
    NAV_ITEMS.map((item) => item.path)
      .filter((path) => (path === '/' ? location.pathname === '/' : location.pathname.startsWith(path)))
      .at(-1) ?? '/'

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <Layout className="app-layout">
      <Layout.Header className="app-header">
        <Link to="/" className="app-brand">
          <Logo variant="dark" size={32} />
          <span className="app-tagline">{t('app.tagline')}</span>
        </Link>
        <Space size="middle" wrap>
          <LanguageSwitch />
          <Typography.Text className="app-user">{user?.full_name}</Typography.Text>
          <Button onClick={handleLogout}>{t('nav.logout')}</Button>
        </Space>
      </Layout.Header>
      <Layout>
        <Layout.Sider
          breakpoint="md"
          collapsedWidth={0}
          defaultCollapsed={startsCollapsed()}
          theme="light"
          width={220}
        >
          <Menu mode="inline" selectedKeys={[selected]} items={items} aria-label="main navigation" />
        </Layout.Sider>
        <Layout.Content className="app-content">
          <Outlet />
        </Layout.Content>
      </Layout>
    </Layout>
  )
}
