import { MenuOutlined } from '@ant-design/icons'
import { Button, Drawer, Layout } from 'antd'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Outlet, useLocation } from 'react-router-dom'
import { useLanguage } from '../i18n/useLanguage'
import { ErrorBoundary } from './ErrorBoundary'
import { Sidebar } from './Sidebar'
import { UserMenu } from './UserMenu'

/** Signed-in layout from the design: dark sidebar, white top bar, light content area. */
export function AppShell() {
  const { t } = useTranslation()
  const { language, direction, setLanguage } = useLanguage()
  const location = useLocation()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const otherLanguage = language === 'ar' ? 'en' : 'ar'

  return (
    <Layout className="app-shell">
      <Layout.Sider width={220} className="app-sider">
        <Sidebar />
      </Layout.Sider>
      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        placement={direction === 'rtl' ? 'right' : 'left'}
        size={260}
        closable={false}
        className="app-drawer"
      >
        <Sidebar onNavigate={() => setDrawerOpen(false)} />
      </Drawer>
      <Layout>
        <Layout.Header className="app-topbar">
          <Button
            className="app-menu-button"
            type="text"
            icon={<MenuOutlined />}
            aria-label={t('nav.openMenu')}
            onClick={() => setDrawerOpen(true)}
          />
          <div className="app-topbar-spacer" />
          <Button
            type="text"
            className="language-toggle"
            lang={otherLanguage}
            aria-label={t('language.label')}
            onClick={() => setLanguage(otherLanguage)}
          >
            {t(`language.${otherLanguage}`)}
          </Button>
          <UserMenu />
        </Layout.Header>
        <Layout.Content className="app-content">
          <ErrorBoundary key={location.pathname}>
            <Outlet />
          </ErrorBoundary>
        </Layout.Content>
      </Layout>
    </Layout>
  )
}
