import { App, Button, Flex, Input, Popconfirm, Space, Table, Tag, Typography, type TableProps } from 'antd'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useAuth } from '../../auth/context'
import { useSetUserActive, useUsers, type User } from './api'

const PAGE_SIZE = 25

export function UsersPage() {
  const { t, i18n } = useTranslation()
  const { message } = App.useApp()
  const { user: me } = useAuth()
  const [page, setPage] = useState(1)
  const [q, setQ] = useState('')
  const { data, isFetching } = useUsers({ page, pageSize: PAGE_SIZE, q })
  const setActive = useSetUserActive()

  const toggleActive = async (user: User) => {
    await setActive.mutateAsync({ id: user.id, active: !user.is_active })
    message.success(t(user.is_active ? 'users.deactivated' : 'users.activated'))
  }

  const columns: TableProps<User>['columns'] = [
    {
      title: t('users.name'),
      dataIndex: 'full_name',
      render: (name: string, user) => <Link to={`/users/${user.id}`}>{name}</Link>,
    },
    { title: t('users.email'), dataIndex: 'email' },
    {
      title: t('users.roles'),
      dataIndex: 'role_codes',
      render: (roles: string[]) => (
        <Space size={[4, 4]} wrap>
          {roles.map((role) => (
            <Tag key={role}>{t(`roles.${role}`)}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t('users.status'),
      dataIndex: 'is_active',
      render: (active: boolean) =>
        active ? <Tag color="green">{t('users.active')}</Tag> : <Tag>{t('users.inactive')}</Tag>,
    },
    {
      title: t('users.lastLogin'),
      dataIndex: 'last_login_at',
      render: (value: string | null) =>
        value ? new Date(value).toLocaleString(i18n.resolvedLanguage) : t('users.never'),
    },
    {
      title: t('users.actions'),
      key: 'actions',
      render: (_, user) =>
        user.id === me?.id ? null : user.is_active ? (
          <Popconfirm title={t('users.deactivateConfirm')} onConfirm={() => toggleActive(user)}>
            <Button size="small" danger>
              {t('users.deactivate')}
            </Button>
          </Popconfirm>
        ) : (
          <Button size="small" onClick={() => toggleActive(user)}>
            {t('users.activate')}
          </Button>
        ),
    },
  ]

  return (
    <Space orientation="vertical" size="middle" className="page">
      <Flex justify="space-between" align="center" wrap gap="middle">
        <Typography.Title level={2}>{t('users.title')}</Typography.Title>
        <Link to="/users/new">
          <Button type="primary">{t('users.new')}</Button>
        </Link>
      </Flex>
      <Input.Search
        allowClear
        placeholder={t('users.search')}
        aria-label={t('users.search')}
        onSearch={(value) => {
          setQ(value)
          setPage(1)
        }}
        className="search-box"
      />
      <Table<User>
        rowKey="id"
        columns={columns}
        dataSource={data?.items}
        loading={isFetching}
        scroll={{ x: true }}
        pagination={{
          current: page,
          pageSize: PAGE_SIZE,
          total: data?.total ?? 0,
          showSizeChanger: false,
          onChange: setPage,
        }}
      />
    </Space>
  )
}
