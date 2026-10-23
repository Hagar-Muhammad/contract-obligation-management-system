import { SearchOutlined } from '@ant-design/icons'
import { DatePicker, Input, Select, Table, type TableProps } from 'antd'
import { useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { PageHeader } from '../../components/PageHeader'
import { useListSearch } from '../../components/useListSearch'
import { UserAvatar } from '../../components/UserAvatar'
import { useLanguage } from '../../i18n/useLanguage'
import { useRelativeTime } from '../../i18n/useRelativeTime'
import { useAuditLogs, type AuditAction, type AuditLog } from './api'

const PAGE_SIZE = 25

type Tone = 'blue' | 'green' | 'amber' | 'red' | 'grey'

/** Dot colour per action, as in the Activity panel of the design. Typed as a Record so every action is covered. */
const ACTION_TONE: Record<AuditAction, Tone> = {
  'auth.login': 'blue',
  'auth.logout': 'grey',
  'auth.login_failed': 'red',
  'auth.refresh_token_reused': 'red',
  'user.created': 'green',
  'user.registered': 'green',
  'user.updated': 'blue',
  'user.password_reset': 'amber',
  'user.deactivated': 'red',
  'user.activated': 'green',
  'party.created': 'green',
  'party.updated': 'blue',
  'property.created': 'green',
  'property.updated': 'blue',
}

const ACTION_GROUPS = ['auth', 'user', 'party', 'property'] as const

/** Where each kind of record opens in the app. */
const TARGET_PATH: Record<AuditLog['target_type'], string> = {
  user: '/users',
  party: '/parties',
  property: '/properties',
}

/** Local calendar day "YYYY-MM-DD" → ISO instant at the start of that day (or of the next day). */
function dayStart(day: string, addDays = 0): string {
  const date = new Date(`${day}T00:00:00`)
  date.setDate(date.getDate() + addDays)
  return date.toISOString()
}

function ChangeValue({ field, value }: { field: string; value: unknown }) {
  const { t } = useTranslation()
  if (value === null || value === undefined || value === '') return <span className="audit-empty">—</span>
  if (field === 'roles' && Array.isArray(value)) {
    return <>{value.map((code) => t(`roles.${String(code)}`)).join(', ')}</>
  }
  if (field === 'is_active') return <>{value ? t('users.active') : t('users.inactive')}</>
  if (field === 'preferred_language') return <>{t(`language.${String(value)}`)}</>
  if (field === 'party_type') return <>{t(`partyTypes.${String(value)}`)}</>
  if (field === 'property_type') return <>{t(`propertyTypes.${String(value)}`)}</>
  if (Array.isArray(value)) return <>{value.join(', ')}</>
  return <>{String(value)}</>
}

function AuditDetails({ entry }: { entry: AuditLog }) {
  const { t } = useTranslation()
  const changes = Object.entries(entry.changes ?? {})
  return (
    <div className="audit-details">
      {changes.length > 0 && (
        <table className="audit-changes">
          <thead>
            <tr>
              <th>{t('audit.field')}</th>
              <th>{t('audit.before')}</th>
              <th>{t('audit.after')}</th>
            </tr>
          </thead>
          <tbody>
            {changes.map(([field, [before, after]]) => (
              <tr key={field}>
                <td>{t(`audit.fields.${field}`, { defaultValue: field })}</td>
                <td>
                  <ChangeValue field={field} value={before} />
                </td>
                <td>
                  <ChangeValue field={field} value={after} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <dl className="audit-meta">
        <dt>{t('audit.requestId')}</dt>
        <dd>{entry.request_id ?? '—'}</dd>
        <dt>{t('audit.ipAddress')}</dt>
        <dd>{entry.ip_address ?? '—'}</dd>
      </dl>
    </div>
  )
}

/** Audit log (FR-AUD-02): read-only, newest first. Styled after the design's Activity panel and Users table. */
export function AuditLogPage() {
  const { t } = useTranslation()
  const { language } = useLanguage()
  const relativeTime = useRelativeTime()
  const { search, setSearch, query, page, setPage } = useListSearch()
  const [action, setAction] = useState<AuditAction>()
  const [range, setRange] = useState<{ from?: string; to?: string }>({})
  const logs = useAuditLogs({ page, pageSize: PAGE_SIZE, q: query, action, ...range })
  const dateTime = new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeStyle: 'short' })

  const actor = (entry: AuditLog): ReactNode => {
    if (entry.actor) {
      return (
        <span className="person">
          <UserAvatar name={entry.actor.full_name} size={28} />
          <span className="person-text">
            <bdi className="person-name">{entry.actor.full_name}</bdi>
            <span className="person-email">{entry.actor.email}</span>
          </span>
        </span>
      )
    }
    return entry.actor_type === 'system' ? (
      <span className="pill pill-grey">{t('audit.system')}</span>
    ) : (
      <span className="pill pill-amber">{t('audit.anonymous')}</span>
    )
  }

  const target = (entry: AuditLog): ReactNode => {
    const label = entry.target_label ?? '—'
    return (
      <span className="person-text">
        {entry.target_id ? (
          <Link to={`${TARGET_PATH[entry.target_type]}/${entry.target_id}`} className="person-name">
            <bdi>{label}</bdi>
          </Link>
        ) : (
          <bdi className="person-name">{label}</bdi>
        )}
        <span className="person-email">{t(`audit.targets.${entry.target_type}`)}</span>
      </span>
    )
  }

  const columns: TableProps<AuditLog>['columns'] = [
    {
      title: t('audit.colWhen'),
      dataIndex: 'occurred_at',
      width: 190,
      render: (iso: string) => (
        <span className="person-text">
          <span>{dateTime.format(new Date(iso))}</span>
          <span className="person-email">{relativeTime(iso)}</span>
        </span>
      ),
    },
    { title: t('audit.colActor'), key: 'actor', render: (_, entry) => actor(entry) },
    {
      title: t('audit.colAction'),
      dataIndex: 'action',
      render: (value: AuditAction) => (
        <span className={`audit-action tone-dot-${ACTION_TONE[value]}`}>{t(`audit.actions.${value}`)}</span>
      ),
    },
    { title: t('audit.colTarget'), key: 'target', render: (_, entry) => target(entry) },
  ]

  return (
    <div className="page">
      <PageHeader title={t('audit.title')} subtitle={t('audit.subtitle')} />
      <section className="panel panel-flush">
        <div className="panel-toolbar list-toolbar">
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder={t('audit.search')}
            aria-label={t('audit.search')}
            className="search-box"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Select<AuditAction>
            allowClear
            className="list-filter"
            placeholder={t('audit.allActions')}
            aria-label={t('audit.actionFilter')}
            value={action}
            onChange={(value) => {
              setAction(value)
              setPage(1)
            }}
            options={ACTION_GROUPS.map((group) => ({
              label: t(`audit.groups.${group}`),
              title: t(`audit.groups.${group}`),
              options: (Object.keys(ACTION_TONE) as AuditAction[])
                .filter((value) => value.startsWith(`${group}.`))
                .map((value) => ({ value, label: t(`audit.actions.${value}`) })),
            }))}
          />
          <DatePicker.RangePicker
            aria-label={t('audit.dateFilter')}
            className="list-filter"
            allowEmpty={[true, true]}
            onChange={(_, [from, to]) => {
              setRange({ from: from ? dayStart(from) : undefined, to: to ? dayStart(to, 1) : undefined })
              setPage(1)
            }}
          />
        </div>
        <Table<AuditLog>
          rowKey="id"
          columns={columns}
          dataSource={logs.data?.items}
          loading={logs.isFetching}
          scroll={{ x: 860 }}
          expandable={{ expandedRowRender: (entry) => <AuditDetails entry={entry} /> }}
          locale={{ emptyText: t('audit.empty') }}
          pagination={{
            current: page,
            pageSize: PAGE_SIZE,
            total: logs.data?.total ?? 0,
            showSizeChanger: false,
            hideOnSinglePage: true,
            onChange: setPage,
          }}
        />
      </section>
      <p className="audit-note">{t('audit.readOnlyNote')}</p>
    </div>
  )
}
