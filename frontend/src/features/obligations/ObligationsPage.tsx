import { PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { Button, Checkbox, DatePicker, Input, Select, Table, type TableProps } from 'antd'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { PERMISSIONS, useAuth } from '../../auth/context'
import { PageHeader } from '../../components/PageHeader'
import { useListSearch } from '../../components/useListSearch'
import { ContractSelect } from '../contracts/pickers'
import {
  PRIORITIES,
  useObligationCounts,
  useObligations,
  type Obligation,
  type ObligationSort,
  type ObligationView,
  type Priority,
} from './api'
import { ObligationPanel } from './ObligationPanel'
import { useObligationFormat } from './useObligationFormat'
import { UserSelect } from './UserSelect'

const PAGE_SIZE = 25
const VIEWS: ObligationView[] = [
  'open',
  'overdue',
  'due_this_week',
  'in_progress',
  'pending',
  'completed',
  'cancelled',
]
const SORTS: ObligationSort[] = ['due_date', '-due_date', 'priority', 'title', '-updated_at']

/** Obligations (docs/design/ConTrack-UI.pdf, screen 7; FR-OBL-04, FR-OBL-05, FR-OBL-07, FR-SEARCH-03). */
export function ObligationsPage() {
  const { t } = useTranslation()
  const { can } = useAuth()
  const navigate = useNavigate()
  const { id: selectedId } = useParams()
  const [searchParams] = useSearchParams()
  const format = useObligationFormat()
  const { search, setSearch, query, page, setPage } = useListSearch()
  const [view, setView] = useState<ObligationView>('open')
  // "View all" links open the list for one contract or property (FR-PROP-02).
  const [contractId, setContractId] = useState(searchParams.get('contract') ?? undefined)
  const propertyId = searchParams.get('property') ?? undefined
  const [ownerId, setOwnerId] = useState<string | null>(null)
  const [priority, setPriority] = useState<Priority>()
  const [due, setDue] = useState<{ from?: string; to?: string }>({})
  const [mine, setMine] = useState(false)
  const [sort, setSort] = useState<ObligationSort>('due_date')
  const obligations = useObligations({
    page,
    pageSize: PAGE_SIZE,
    view,
    q: query,
    contractId,
    propertyId,
    responsibleUserId: ownerId ?? undefined,
    mine,
    priority,
    dueFrom: due.from,
    dueTo: due.to,
    sort,
  })
  const counts = useObligationCounts()
  const canPickUsers = can(PERMISSIONS.obligationCreate) || can(PERMISSIONS.obligationUpdate)
  const filtered =
    <T,>(setter: (value: T) => void) =>
    (value: T) => {
      setter(value)
      setPage(1)
    }

  const columns: TableProps<Obligation>['columns'] = [
    {
      title: t('obligations.colObligation'),
      dataIndex: 'title',
      render: (_, o) => (
        <span className="person-text">
          <bdi className="person-name">{o.title}</bdi>
          <span className="person-email">
            <bdi dir="ltr">{o.contract.contract_number}</bdi> · {format.repeats(o.recurrence_rule)}
          </span>
        </span>
      ),
    },
    {
      title: t('obligations.colResponsible'),
      key: 'responsible',
      render: (_, o) => (
        <span className="person-text">
          <bdi>{o.responsible_party.display_name}</bdi>
          {o.responsible_user && (
            <span className="person-email">
              <bdi>{o.responsible_user.full_name}</bdi>
            </span>
          )}
        </span>
      ),
    },
    {
      title: t('obligations.colDue'),
      key: 'due',
      render: (_, o) => {
        const d = format.due(o)
        return (
          <span className={`person-text ${d.late ? 'text-danger' : ''}`}>
            <span>{d.date}</span>
            {d.note && <span className={d.late ? '' : 'person-email'}>{d.note}</span>}
          </span>
        )
      },
    },
    {
      title: t('obligations.colPriority'),
      dataIndex: 'priority',
      render: (value: Priority) => {
        const p = format.priority(value)
        return (
          <span className={p.className}>
            {p.marks && <span aria-hidden="true">{p.marks} </span>}
            {p.label}
          </span>
        )
      },
    },
    {
      title: t('obligations.colStatus'),
      key: 'status',
      render: (_, o) => {
        const s = format.status(o)
        return <span className={s.className}>{s.label}</span>
      },
    },
  ]

  const chip = (key: ObligationView) => (
    <button
      key={key}
      type="button"
      className={`status-chip ${view === key ? 'is-active' : ''} ${key === 'overdue' ? 'is-danger' : ''}`}
      aria-pressed={view === key}
      onClick={() => filtered(setView)(key)}
    >
      {t(`obligations.views.${key}`)} <span className="chip-count">{counts.data?.[key] ?? '·'}</span>
    </button>
  )

  return (
    <div className="page">
      <PageHeader
        title={t('obligations.title')}
        subtitle={t('obligations.subtitle')}
        actions={
          can(PERMISSIONS.obligationCreate) && (
            <Link to={contractId ? `/obligations/new?contract=${contractId}` : '/obligations/new'}>
              <Button type="primary" icon={<PlusOutlined />}>
                {t('obligations.new')}
              </Button>
            </Link>
          )
        }
      />
      <div className="status-chips" role="group" aria-label={t('obligations.statusFilter')}>
        {VIEWS.map(chip)}
      </div>
      <div className={selectedId ? 'obligations-layout has-panel' : 'obligations-layout'}>
        <section className="panel panel-flush">
          <div className="panel-toolbar list-toolbar">
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder={t('obligations.search')}
              aria-label={t('obligations.search')}
              className="search-box"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <ContractSelect
              className="filter-select"
              placeholder={t('obligations.anyContract')}
              ariaLabel={t('obligations.contractFilter')}
              value={contractId}
              onChange={filtered(setContractId)}
            />
            {canPickUsers && (
              <UserSelect
                className="filter-select"
                placeholder={t('obligations.anyOwner')}
                ariaLabel={t('obligations.ownerFilter')}
                value={ownerId}
                onChange={filtered(setOwnerId)}
              />
            )}
            <Select<Priority>
              allowClear
              className="filter-select"
              placeholder={t('obligations.anyPriority')}
              aria-label={t('obligations.priorityFilter')}
              value={priority}
              onChange={filtered(setPriority)}
              options={PRIORITIES.map((value) => ({ value, label: t(`obligations.priorities.${value}`) }))}
            />
            <DatePicker.RangePicker
              className="filter-select"
              allowEmpty={[true, true]}
              placeholder={[t('obligations.dueFrom'), t('obligations.dueTo')]}
              aria-label={t('obligations.dueFilter')}
              onChange={(_, [from, to]) => filtered(setDue)({ from: from || undefined, to: to || undefined })}
            />
            <Checkbox checked={mine} onChange={(e) => filtered(setMine)(e.target.checked)}>
              {t('obligations.onlyMine')}
            </Checkbox>
            <span className="toolbar-end">
              <Select<ObligationSort>
                className="filter-select"
                aria-label={t('contracts.sort')}
                value={sort}
                onChange={filtered(setSort)}
                options={SORTS.map((value) => ({ value, label: t(`obligations.sorts.${value}`) }))}
              />
            </span>
          </div>
          <Table<Obligation>
            rowKey="id"
            columns={columns}
            dataSource={obligations.data?.items}
            loading={obligations.isFetching}
            scroll={{ x: 760 }}
            rowClassName={(o) => (o.id === selectedId ? 'is-selected' : 'is-clickable')}
            onRow={(o) => ({
              onClick: () => navigate(`/obligations/${o.id}${window.location.search}`),
              onKeyDown: (event) => {
                if (event.key === 'Enter') navigate(`/obligations/${o.id}${window.location.search}`)
              },
              tabIndex: 0,
            })}
            locale={{ emptyText: t(`obligations.empty.${view}`) }}
            pagination={{
              current: page,
              pageSize: PAGE_SIZE,
              total: obligations.data?.total ?? 0,
              showSizeChanger: false,
              hideOnSinglePage: true,
              onChange: setPage,
              showTotal: (total, [from, to]) => t('obligations.showing', { from, to, total }),
            }}
          />
        </section>
        {selectedId && (
          <ObligationPanel
            key={selectedId}
            obligationId={selectedId}
            onClose={() => navigate(`/obligations${window.location.search}`)}
          />
        )}
      </div>
    </div>
  )
}
