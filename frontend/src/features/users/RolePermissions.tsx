import { CheckOutlined } from '@ant-design/icons'
import { Table, type TableProps } from 'antd'
import { useTranslation } from 'react-i18next'
import { ROLE_CODES } from '../../auth/roles'
import type { Role } from './api'

/** SRS 3.2 rows, each backed by the permission code the backend enforces. */
const CAPABILITIES = [
  { key: 'viewContracts', permission: 'contract:view' },
  { key: 'editContracts', permission: 'contract:edit' },
  { key: 'archiveContracts', permission: 'contract:archive' },
  { key: 'uploadDocuments', permission: 'document:upload' },
  { key: 'confirmExtraction', permission: 'extraction:confirm' },
  { key: 'createObligations', permission: 'obligation:create' },
  { key: 'updateObligations', permission: 'obligation:update' },
  { key: 'manageUsers', permission: 'user:manage' },
  { key: 'viewReports', permission: 'report:view' },
] as const

type Cell = 'full' | 'scoped' | 'limited' | 'viewOnly' | 'none'

function cell(role: Role, permission: string): Cell {
  const granted = role.permissions.includes(permission)
  if (!granted) {
    // "Update assigned obligations: View" in SRS 3.2 — can see obligations but not change them.
    return permission === 'obligation:update' && role.permissions.includes('obligation:view')
      ? 'viewOnly'
      : 'none'
  }
  if (role.scoped_permissions.includes(permission)) return 'scoped'
  // "View reports: Limited" — reports only count the obligations assigned to the user.
  if (permission === 'report:view' && role.data_scope === 'assigned_obligations') return 'limited'
  return 'full'
}

function CellValue({ value }: { value: Cell }) {
  const { t } = useTranslation()
  switch (value) {
    case 'full':
      return <CheckOutlined className="matrix-check" aria-label={t('matrix.legendFull')} />
    case 'scoped':
      return <span className="pill pill-amber">{t('matrix.scoped')}</span>
    case 'limited':
      return <span className="pill pill-amber">{t('matrix.limited')}</span>
    case 'viewOnly':
      return <span className="pill pill-grey">{t('matrix.viewOnly')}</span>
    default:
      return (
        <span className="matrix-none" aria-label={t('matrix.legendNone')}>
          —
        </span>
      )
  }
}

interface Row {
  key: string
  permission: string
}

/** The SRS 3.2 matrix, rendered from the roles API so it always shows what the server enforces. */
export function RolePermissions({ roles }: { roles: Role[] }) {
  const { t } = useTranslation()
  const byCode = new Map(roles.map((role) => [role.code, role]))
  const ordered = ROLE_CODES.map((code) => byCode.get(code)).filter((r): r is Role => Boolean(r))

  const columns: TableProps<Row>['columns'] = [
    {
      title: t('matrix.capability'),
      dataIndex: 'key',
      render: (key: string) => <strong className="matrix-capability">{t(`matrix.${key}`)}</strong>,
    },
    ...ordered.map((role) => ({
      title: t(`rolesShort.${role.code}`),
      key: role.code,
      align: 'center' as const,
      render: (_: unknown, row: Row) => <CellValue value={cell(role, row.permission)} />,
    })),
  ]

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">{t('matrix.title')}</h2>
          <p className="panel-subtitle">{t('matrix.subtitle')}</p>
        </div>
        <span className="pill pill-amber pill-dot">{t('matrix.proposed')}</span>
      </div>
      <Table<Row>
        rowKey="key"
        columns={columns}
        dataSource={CAPABILITIES.map((c) => ({ key: c.key, permission: c.permission }))}
        pagination={false}
        size="middle"
        scroll={{ x: 760 }}
        className="matrix-table"
      />
      <div className="matrix-legend">
        <span>
          <CheckOutlined className="matrix-check" /> {t('matrix.legendFull')}
        </span>
        <span>
          <span className="pill pill-amber">{t('matrix.scoped')}</span> {t('matrix.legendScoped')}
        </span>
        <span>
          <span className="matrix-none">—</span> {t('matrix.legendNone')}
        </span>
      </div>
    </section>
  )
}
