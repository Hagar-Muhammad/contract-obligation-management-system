import { EllipsisOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { App, Button, DatePicker, Dropdown, Input, Select, Table, Tabs, type TableProps } from 'antd'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { PERMISSIONS, useAuth } from '../../auth/context'
import { PageHeader } from '../../components/PageHeader'
import { useListSearch } from '../../components/useListSearch'
import {
  useContractCounts,
  useContractDefaults,
  useContracts,
  useContractTypes,
  useSetArchived,
  type Contract,
  type ContractSort,
  type ContractView,
} from './api'
import { PartySelect, PropertySelect } from './pickers'
import { useContractFormat } from './useContractFormat'

const PAGE_SIZE = 25
const VIEWS: ContractView[] = ['active', 'draft', 'expiring', 'ended', 'archived']
const SORTS: ContractSort[] = [
  'end_date',
  '-end_date',
  'start_date',
  '-start_date',
  'contract_number',
  'title',
  '-updated_at',
]

function RowActions({ contract }: { contract: Contract }) {
  const { t } = useTranslation()
  const { can } = useAuth()
  const { modal, message } = App.useApp()
  const navigate = useNavigate()
  const setArchived = useSetArchived(contract.id)
  const archived = Boolean(contract.archived_at)

  const toggleArchive = () =>
    modal.confirm({
      title: archived ? t('contracts.restoreConfirm') : t('contracts.archiveConfirm'),
      content: archived ? undefined : t('contracts.archiveHelp'),
      okText: archived ? t('contracts.restore') : t('contracts.archive'),
      cancelText: t('common.cancel'),
      onOk: async () => {
        await setArchived.mutateAsync(!archived)
        message.success(archived ? t('contracts.restored') : t('contracts.archivedDone'))
      },
    })

  const items = [
    { key: 'view', label: t('contracts.view'), onClick: () => navigate(`/contracts/${contract.id}`) },
    ...(can(PERMISSIONS.contractEdit) && !archived
      ? [
          {
            key: 'edit',
            label: t('contracts.edit'),
            onClick: () => navigate(`/contracts/${contract.id}/edit`),
          },
        ]
      : []),
    ...(can(PERMISSIONS.contractArchive)
      ? [
          {
            key: 'archive',
            label: archived ? t('contracts.restore') : t('contracts.archive'),
            onClick: toggleArchive,
          },
        ]
      : []),
  ]
  return (
    <Dropdown menu={{ items }} trigger={['click']}>
      <Button
        type="text"
        icon={<EllipsisOutlined />}
        aria-label={t('contracts.actionsFor', { number: contract.contract_number })}
      />
    </Dropdown>
  )
}

/** Contracts (docs/design/ConTrack-UI.pdf, screen 3; FR-CON-03, FR-CON-05, FR-SEARCH-01/02, BR-07). */
export function ContractsPage() {
  const { t } = useTranslation()
  const { can } = useAuth()
  const format = useContractFormat()
  const [searchParams] = useSearchParams()
  const { search, setSearch, query, page, setPage } = useListSearch()
  const [view, setView] = useState<ContractView>('active')
  const [typeCode, setTypeCode] = useState<string>()
  const [partyId, setPartyId] = useState<string>()
  // "All contracts for this property" links open the list filtered by ?property=<id> (FR-PROP-02).
  const [propertyId, setPropertyId] = useState<string | undefined>(searchParams.get('property') ?? undefined)
  const [term, setTerm] = useState<{ from?: string; to?: string }>({})
  const [sort, setSort] = useState<ContractSort>('end_date')
  const contracts = useContracts({
    page,
    pageSize: PAGE_SIZE,
    view,
    q: query,
    typeCode,
    partyId,
    propertyId,
    termFrom: term.from,
    termTo: term.to,
    sort,
  })
  const counts = useContractCounts()
  const types = useContractTypes()
  const defaults = useContractDefaults()
  const expiringDays = defaults.data?.expiring_soon_days ?? 60
  const filtered =
    <T,>(setter: (value: T) => void) =>
    (value: T) => {
      setter(value)
      setPage(1)
    }

  const columns: TableProps<Contract>['columns'] = [
    {
      title: t('contracts.colContract'),
      dataIndex: 'title',
      render: (_, contract) => (
        <Link to={`/contracts/${contract.id}`} className="person-text">
          <bdi className="contract-title">{contract.title}</bdi>
          <span className="person-email" dir="ltr">
            {contract.contract_number}
          </span>
        </Link>
      ),
    },
    {
      title: t('contracts.colType'),
      key: 'type',
      render: (_, contract) => <span className="type-tag">{format.name(contract.contract_type)}</span>,
    },
    {
      title: t('contracts.colParties'),
      key: 'parties',
      render: (_, contract) => {
        const [first, ...rest] = contract.parties
        return (
          <span className="person-text">
            <bdi>{first?.display_name}</bdi>
            {rest.length > 0 && (
              <span className="person-email">
                + <bdi>{rest[0].display_name}</bdi>
                {rest.length > 1 && ` ${t('contracts.andMore', { count: rest.length - 1 })}`}
              </span>
            )}
          </span>
        )
      },
    },
    {
      title: t('contracts.colProperty'),
      key: 'property',
      render: (_, contract) =>
        contract.properties.length ? (
          <span className="person-text">
            <bdi>{contract.properties[0].name}</bdi>
            {contract.properties.length > 1 && (
              <span className="person-email">
                {t('contracts.andMore', { count: contract.properties.length - 1 })}
              </span>
            )}
          </span>
        ) : (
          <span className="muted">—</span>
        ),
    },
    { title: t('contracts.colTerm'), key: 'term', render: (_, contract) => format.term(contract) },
    {
      title: t('contracts.colValue'),
      key: 'value',
      align: 'end',
      render: (_, contract) => (
        <strong className="nowrap" dir="ltr">
          {format.money(contract, true)}
        </strong>
      ),
    },
    {
      title: t('contracts.colStatus'),
      key: 'status',
      render: (_, contract) => {
        const status = format.status(contract, expiringDays)
        return (
          <span className="person-text">
            <span className={status.className}>{status.label}</span>
            {status.note && <span className="person-email">{status.note}</span>}
          </span>
        )
      },
    },
    {
      title: t('contracts.colObligations'),
      key: 'obligations',
      render: (_, contract) => (
        <span className="nowrap">
          {t('obligations.openCount', { count: contract.obligations.open })}
          {contract.obligations.overdue > 0 && (
            <span className="text-danger">
              {' · '}
              {t('obligations.overdueCount', { count: contract.obligations.overdue })}
            </span>
          )}
        </span>
      ),
    },
    { key: 'actions', width: 56, render: (_, contract) => <RowActions contract={contract} /> },
  ]

  const tabLabel = (key: ContractView) => (
    <span>
      {t(`contracts.views.${key}`)} <span className="tab-count">{counts.data?.[key] ?? '·'}</span>
    </span>
  )

  return (
    <div className="page">
      <PageHeader
        title={t('contracts.title')}
        subtitle={t('contracts.subtitle')}
        actions={
          can(PERMISSIONS.contractCreate) && (
            <Link to="/contracts/new">
              <Button type="primary" icon={<PlusOutlined />}>
                {t('contracts.new')}
              </Button>
            </Link>
          )
        }
      />
      <Tabs
        activeKey={view}
        onChange={(key) => filtered(setView)(key as ContractView)}
        items={VIEWS.map((key) => ({ key, label: tabLabel(key) }))}
      />
      <section className="panel panel-flush">
        <div className="panel-toolbar list-toolbar">
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder={t('contracts.search')}
            aria-label={t('contracts.search')}
            className="search-box"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Select<string>
            allowClear
            className="filter-select"
            placeholder={t('contracts.anyType')}
            aria-label={t('contracts.typeFilter')}
            value={typeCode}
            onChange={filtered(setTypeCode)}
            options={(types.data ?? []).map((type) => ({ value: type.code, label: format.name(type) }))}
          />
          <PartySelect
            className="filter-select"
            placeholder={t('contracts.anyParty')}
            ariaLabel={t('contracts.partyFilter')}
            value={partyId}
            onChange={(id) => filtered(setPartyId)(id)}
          />
          <PropertySelect
            className="filter-select"
            placeholder={t('contracts.anyProperty')}
            ariaLabel={t('contracts.propertyFilter')}
            value={propertyId}
            onChange={(value) => filtered(setPropertyId)(value as string | undefined)}
          />
          <DatePicker.RangePicker
            className="filter-select"
            allowEmpty={[true, true]}
            placeholder={[t('contracts.termFrom'), t('contracts.termTo')]}
            aria-label={t('contracts.dateFilter')}
            onChange={(_, [from, to]) => filtered(setTerm)({ from: from || undefined, to: to || undefined })}
          />
          <span className="toolbar-end">
            <span className="muted">{t('contracts.sort')}</span>
            <Select<ContractSort>
              className="filter-select"
              aria-label={t('contracts.sort')}
              value={sort}
              onChange={filtered(setSort)}
              options={SORTS.map((value) => ({ value, label: t(`contracts.sorts.${value}`) }))}
            />
          </span>
        </div>
        <Table<Contract>
          rowKey="id"
          columns={columns}
          dataSource={contracts.data?.items}
          loading={contracts.isFetching}
          scroll={{ x: 1160 }}
          locale={{ emptyText: t(`contracts.empty.${view}`) }}
          pagination={{
            current: page,
            pageSize: PAGE_SIZE,
            total: contracts.data?.total ?? 0,
            showSizeChanger: false,
            hideOnSinglePage: true,
            onChange: setPage,
            showTotal: (total, [from, to]) => t('contracts.showing', { from, to, total }),
          }}
        />
      </section>
    </div>
  )
}
