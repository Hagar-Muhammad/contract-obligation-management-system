import {
  AppstoreOutlined,
  AuditOutlined,
  BankOutlined,
  BarChartOutlined,
  CheckSquareOutlined,
  ControlOutlined,
  FileTextOutlined,
  ScanOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import type { ReactNode } from 'react'
import { PERMISSIONS } from '../auth/context'

export interface NavItem {
  path: string
  labelKey: string
  icon: ReactNode
  /** Hidden from users without this permission (the backend enforces it regardless). */
  permission?: string
  /** Delivery-plan module that builds the page; until then it shows a "coming soon" page. */
  module?: number
}

export interface NavSection {
  titleKey: string
  items: NavItem[]
}

/** Sidebar from docs/design/ConTrack-UI.pdf. */
export const NAV_SECTIONS: NavSection[] = [
  {
    titleKey: 'nav.workspace',
    items: [
      { path: '/', labelKey: 'nav.dashboard', icon: <AppstoreOutlined /> },
      {
        path: '/contracts',
        labelKey: 'nav.contracts',
        icon: <FileTextOutlined />,
        permission: PERMISSIONS.contractView,
        module: 4,
      },
      {
        path: '/obligations',
        labelKey: 'nav.obligations',
        icon: <CheckSquareOutlined />,
        permission: PERMISSIONS.obligationView,
        module: 6,
      },
      {
        path: '/review-queue',
        labelKey: 'nav.reviewQueue',
        icon: <ScanOutlined />,
        permission: PERMISSIONS.extractionConfirm,
        module: 9,
      },
      {
        path: '/parties',
        labelKey: 'nav.parties',
        icon: <TeamOutlined />,
        permission: PERMISSIONS.contractView,
        module: 3,
      },
      {
        path: '/properties',
        labelKey: 'nav.properties',
        icon: <BankOutlined />,
        permission: PERMISSIONS.contractView,
        module: 3,
      },
    ],
  },
  {
    titleKey: 'nav.insights',
    items: [
      {
        path: '/reports',
        labelKey: 'nav.reports',
        icon: <BarChartOutlined />,
        permission: PERMISSIONS.reportView,
        module: 10,
      },
      {
        path: '/audit-log',
        labelKey: 'nav.auditLog',
        icon: <AuditOutlined />,
        permission: PERMISSIONS.auditView,
        module: 2,
      },
    ],
  },
  {
    titleKey: 'nav.admin',
    items: [
      {
        path: '/users',
        labelKey: 'nav.usersRoles',
        icon: <SafetyCertificateOutlined />,
        permission: PERMISSIONS.userManage,
      },
      {
        path: '/settings',
        labelKey: 'nav.settings',
        icon: <ControlOutlined />,
        permission: PERMISSIONS.roleManage,
        module: 0,
      },
    ],
  },
]

/** Pages linked from the sidebar that later modules build. */
export const UPCOMING_PAGES = NAV_SECTIONS.flatMap((section) => section.items).filter(
  (item) => item.module !== undefined,
)
