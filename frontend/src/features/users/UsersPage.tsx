import { PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { App, Button, Input, Table, Tabs, Tag, type TableProps } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/context'
import { ROLE_CODES, ROLE_TAG_CLASS, scopeKey, type RoleCodeName } from '../../auth/roles'
import { PageHeader } from '../../components/PageHeader'
import { UserAvatar } from '../../components/UserAvatar'
import { useLanguage } from '../../i18n/useLanguage'
import { useRoles, useSetUserActive, useUsers, type Role, type User } from './api'
import { RolePermissions } from './RolePermissions'

const PAGE_SIZE = 25

function useRelativeTime() {
  const { language } = useLanguage()
  const { t } = useTranslation()
  const format = new Intl.RelativeTimeFormat(language, { numeric: 'auto' })
  return (iso: string | null) => {
    if (!iso) return t('users.never')
    const minutes = Math.round((new Date(iso).getTime() - Date.now()) / 60000)
    if (Math.abs(minutes) < 60) return format.format(minutes, 'minute')
    const hours = Math.round(minutes / 60)
    if (Math.abs(hours) < 24) return format.format(hours, 'hour')
    return format.format(Math.round(hours / 24), 'day')
  }
}

function sortedRoles(codes: string[]): RoleCodeName[] {
  return ROLE_CODES.filter((code) => codes.includes(code))
}

/** Users & roles (docs/design/ConTrack-UI.pdf, screen 8; FR-USER-01..03, SRS 3.2). */
export function UsersPage() {
  const { t } = useTranslation()
  const { message } = App.useApp()
  const { user: me } = useAuth()
  const navigate = useNavigate()
  const relativeTime = useRelativeTime()
  const [tab, setTab] = useState('users')
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [q, setQ] = useState('')
  // Query the server once typing pauses, not on every keystroke.
  useEffect(() => {
    const timer = setTimeout(() => {
      setQ(search.trim())
      setPage(1)
    }, 300)
    return () => clearTimeout(timer)
  }, [search])
  const users = useUsers({ page, pageSize: PAGE_SIZE, q })
  const roles = useRoles()
  const setActive = useSetUserActive()

  const reactivate = async (user: User) => {
    await setActive.mutateAsync({ id: user.id, active: true })
    message.success(t('users.activated'))
  }

  const columns: TableProps<User>['columns'] = [
    {
      title: t('users.colName'),
      dataIndex: 'full_name',
      render: (_, user) => (
        <Link to={`/users/${user.id}`} className="person">
          <UserAvatar name={user.full_name} muted={!user.is_active} />
          <span className="person-text">
            <span className="person-name">
              {user.full_name}
              {user.id === me?.id && <span className="person-you"> · {t('users.you')}</span>}
            </span>
            <span className="person-email">{user.email}</span>
          </span>
        </Link>
      ),
    },
    {
      title: t('users.colRole'),
      dataIndex: 'role_codes',
      render: (codes: string[]) => (
        <span className="tag-list">
          {sortedRoles(codes).map((role) => (
            <Tag key={role} className={ROLE_TAG_CLASS[role]}>
              {t(`roles.${role}`)}
            </Tag>
          ))}
        </span>
      ),
    },
    {
      title: t('users.colScope'),
      key: 'scope',
      render: (_, user) => (user.is_active ? t(scopeKey(user.role_codes)) : '—'),
    },
    {
      title: t('users.colStatus'),
      dataIndex: 'is_active',
      render: (active: boolean) =>
        active ? (
          <span className="pill pill-green pill-dot">{t('users.active')}</span>
        ) : (
          <span className="pill pill-grey pill-dot">{t('users.inactive')}</span>
        ),
    },
    {
      title: t('users.colLastActive'),
      dataIndex: 'last_login_at',
      render: (value: string | null) => relativeTime(value),
    },
    {
      title: t('users.colActions'),
      key: 'actions',
      align: 'end',
      render: (_, user) =>
        user.is_active ? (
          <Button onClick={() => navigate(`/users/${user.id}`)}>{t('users.editAction')}</Button>
        ) : (
          <Button onClick={() => reactivate(user)} loading={setActive.isPending}>
            {t('users.reactivate')}
          </Button>
        ),
    },
  ]

  const usersTab = (
    <div className="stack">
      <section className="panel panel-flush">
        <div className="panel-toolbar">
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder={t('users.search')}
            aria-label={t('users.search')}
            className="search-box"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Table<User>
          rowKey="id"
          columns={columns}
          dataSource={users.data?.items}
          loading={users.isFetching}
          scroll={{ x: 860 }}
          pagination={{
            current: page,
            pageSize: PAGE_SIZE,
            total: users.data?.total ?? 0,
            showSizeChanger: false,
            hideOnSinglePage: true,
            onChange: setPage,
          }}
        />
      </section>
      {roles.data && <RolePermissions roles={roles.data} />}
    </div>
  )

  const rolesTab = (
    <div className="role-cards">
      {(roles.data ?? [])
        .slice()
        .sort(
          (a, b) => ROLE_CODES.indexOf(a.code as RoleCodeName) - ROLE_CODES.indexOf(b.code as RoleCodeName),
        )
        .map((role: Role) => (
          <section key={role.code} className="panel role-card">
            <Tag className={ROLE_TAG_CLASS[role.code as RoleCodeName]}>{t(`roles.${role.code}`)}</Tag>
            <p className="role-card-text">{t(`roleDescriptions.${role.code}`)}</p>
            <p className="role-card-meta">
              {t(`scope.${role.data_scope}`)} ·{' '}
              {t('users.permissionCount', { count: role.permissions.length })}
            </p>
          </section>
        ))}
    </div>
  )

  return (
    <div className="page">
      <PageHeader
        title={t('users.title')}
        subtitle={t('users.subtitle')}
        actions={
          <Link to="/users/new">
            <Button type="primary" icon={<PlusOutlined />}>
              {t('users.add')}
            </Button>
          </Link>
        }
      />
      <Tabs
        activeKey={tab}
        onChange={setTab}
        items={[
          {
            key: 'users',
            label: (
              <span>
                {t('users.tabUsers')} <span className="tab-count">{users.data?.total ?? '·'}</span>
              </span>
            ),
            children: usersTab,
          },
          {
            key: 'roles',
            label: (
              <span>
                {t('users.tabRoles')} <span className="tab-count">{roles.data?.length ?? '·'}</span>
              </span>
            ),
            children: rolesTab,
          },
        ]}
      />
    </div>
  )
}
