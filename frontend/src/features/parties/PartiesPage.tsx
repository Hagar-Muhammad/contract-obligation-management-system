import { PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { Button, Input, Segmented, Table, type TableProps } from 'antd'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { PERMISSIONS, useAuth } from '../../auth/context'
import { PageHeader } from '../../components/PageHeader'
import { UserAvatar } from '../../components/UserAvatar'
import { useListSearch } from '../../components/useListSearch'
import { useRelativeTime } from '../../i18n/useRelativeTime'
import { useParties, type Party, type PartyType } from './api'
import { usePartySummary } from './usePartySummary'

const PAGE_SIZE = 25

/** Parties (FR-PARTY-01, FR-PARTY-02): every person and company that takes part in contracts. */
export function PartiesPage() {
  const { t } = useTranslation()
  const { can, user } = useAuth()
  const relativeTime = useRelativeTime()
  const summary = usePartySummary()
  const { search, setSearch, query, page, setPage } = useListSearch()
  const [partyType, setPartyType] = useState<PartyType | 'all'>('all')
  const parties = useParties({
    page,
    pageSize: PAGE_SIZE,
    q: query,
    partyType: partyType === 'all' ? undefined : partyType,
  })
  const canManage = can(PERMISSIONS.partyManage)
  // Mirrors the backend rule (parties/service.py): others only see parties of their own contracts (module 4).
  const seesDirectory = canManage || Boolean(user?.data_scopes.includes('all'))

  const columns: TableProps<Party>['columns'] = [
    {
      title: t('parties.colParty'),
      dataIndex: 'display_name',
      render: (_, party) => (
        <Link to={`/parties/${party.id}`} className="person">
          <UserAvatar name={party.display_name} />
          <span className="person-text">
            <bdi className="person-name">{party.display_name}</bdi>
            <span className="person-email">{summary(party)}</span>
          </span>
        </Link>
      ),
    },
    {
      title: t('parties.colContact'),
      key: 'contact',
      render: (_, party) =>
        party.email || party.phone ? (
          <span className="person-text">
            {party.email && <span>{party.email}</span>}
            {party.phone && (
              <span className="person-email" dir="ltr">
                {party.phone}
              </span>
            )}
          </span>
        ) : (
          <span className="muted">—</span>
        ),
    },
    {
      title: t('parties.colUpdated'),
      dataIndex: 'updated_at',
      width: 160,
      render: (iso: string) => relativeTime(iso),
    },
  ]

  return (
    <div className="page">
      <PageHeader
        title={t('parties.title')}
        subtitle={t('parties.subtitle')}
        actions={
          canManage && (
            <Link to="/parties/new">
              <Button type="primary" icon={<PlusOutlined />}>
                {t('parties.add')}
              </Button>
            </Link>
          )
        }
      />
      <section className="panel panel-flush">
        <div className="panel-toolbar list-toolbar">
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder={t('parties.search')}
            aria-label={t('parties.search')}
            className="search-box"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Segmented<PartyType | 'all'>
            value={partyType}
            onChange={(value) => {
              setPartyType(value)
              setPage(1)
            }}
            options={[
              { value: 'all', label: t('parties.allTypes') },
              { value: 'individual', label: t('parties.individuals') },
              { value: 'organization', label: t('parties.organizations') },
            ]}
          />
        </div>
        <Table<Party>
          rowKey="id"
          columns={columns}
          dataSource={parties.data?.items}
          loading={parties.isFetching}
          scroll={{ x: 720 }}
          locale={{ emptyText: seesDirectory ? t('parties.empty') : t('parties.emptyScoped') }}
          pagination={{
            current: page,
            pageSize: PAGE_SIZE,
            total: parties.data?.total ?? 0,
            showSizeChanger: false,
            hideOnSinglePage: true,
            onChange: setPage,
          }}
        />
      </section>
    </div>
  )
}
