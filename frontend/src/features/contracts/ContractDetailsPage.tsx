import { EditOutlined, InboxOutlined, UndoOutlined } from '@ant-design/icons'
import { Alert, App, Button, Spin } from 'antd'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { PERMISSIONS, useAuth } from '../../auth/context'
import { UserAvatar } from '../../components/UserAvatar'
import { useRelativeTime } from '../../i18n/useRelativeTime'
import {
  useContract,
  useContractActivity,
  useContractDefaults,
  useContractStatuses,
  useSetArchived,
  type Activity,
  type Contract,
} from './api'
import { useContractFormat } from './useContractFormat'

const ACTIVITY_TONE: Record<string, string> = {
  'contract.created': 'green',
  'contract.updated': 'blue',
  'contract.status_changed': 'blue',
  'contract.archived': 'grey',
  'contract.restored': 'green',
}

function ActivityList({ contract }: { contract: Contract }) {
  const { t } = useTranslation()
  const { can } = useAuth()
  const relativeTime = useRelativeTime()
  const format = useContractFormat()
  const activity = useContractActivity(contract.id)
  const statuses = useContractStatuses()
  const statusName = (code: unknown) => {
    const status = statuses.data?.find((s) => s.code === code)
    return status ? format.name(status) : String(code)
  }

  const describe = (entry: Activity) => {
    const changes = entry.changes ?? {}
    switch (entry.action) {
      case 'contract.status_changed': {
        const [from, to] = changes.status ?? []
        return t('contracts.activity.statusChanged', { from: statusName(from), to: statusName(to) })
      }
      case 'contract.updated':
        return t('contracts.activity.updated', {
          fields: Object.keys(changes)
            .map((field) => t(`audit.fields.${field}`, { defaultValue: field }))
            .join(', '),
        })
      default:
        return t(`contracts.activity.${entry.action.split('.')[1]}`)
    }
  }

  return (
    <section className="panel">
      <h2 className="panel-title panel-gap">{t('contracts.activityTitle')}</h2>
      {activity.isLoading ? (
        <Spin />
      ) : (
        <ul className="activity-list">
          {(activity.data ?? []).map((entry, index) => (
            <li
              key={`${entry.occurred_at}-${index}`}
              className={`activity-item tone-dot-${ACTIVITY_TONE[entry.action] ?? 'grey'}`}
            >
              <span>
                <strong>
                  <bdi>{entry.actor?.full_name ?? t('audit.system')}</bdi>
                </strong>{' '}
                {describe(entry)}
              </span>
              <span className="person-email">{relativeTime(entry.occurred_at)}</span>
            </li>
          ))}
        </ul>
      )}
      {can(PERMISSIONS.auditView) && (
        <Link to="/audit-log" className="panel-link">
          {t('contracts.fullAuditLog')}{' '}
          <span className="arrow-forward" aria-hidden="true">
            →
          </span>
        </Link>
      )}
    </section>
  )
}

/** Contract details (docs/design/ConTrack-UI.pdf, screen 4; FR-CON-02, FR-CON-03, FR-CON-05). */
export function ContractDetailsPage() {
  const { id = '' } = useParams()
  const { t } = useTranslation()
  const { can } = useAuth()
  const { modal, message } = App.useApp()
  const navigate = useNavigate()
  const format = useContractFormat()
  const contract = useContract(id)
  const defaults = useContractDefaults()
  const setArchived = useSetArchived(id)

  if (contract.isLoading) return <Spin />
  if (!contract.data) {
    return <Alert type="warning" showIcon message={t('contracts.notFound')} />
  }
  const c = contract.data
  const archived = Boolean(c.archived_at)
  const status = format.status(c, defaults.data?.expiring_soon_days ?? 60)
  const progress = format.progress(c)

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

  return (
    <div className="page">
      <nav className="breadcrumb" aria-label="breadcrumb">
        <Link to="/contracts">{t('contracts.title')}</Link>
        <span className="breadcrumb-sep">/</span>
        <span dir="ltr">{c.contract_number}</span>
      </nav>

      {archived && (
        <Alert
          type="info"
          showIcon
          className="panel-gap"
          message={t('contracts.archivedBanner', { date: format.date(c.archived_at!.slice(0, 10)) })}
        />
      )}

      <section className="panel contract-header">
        <div className="contract-header-top">
          <div>
            <div className="contract-badges">
              <span className={status.className}>{status.label}</span>
              <span className="type-tag">{format.name(c.contract_type)}</span>
              <span className="muted" dir="ltr">
                {c.contract_number}
              </span>
            </div>
            <h1 className="page-title">
              <bdi>{c.title}</bdi>
            </h1>
            <p className="page-subtitle">
              {t('contracts.createdBy', {
                date: format.date(c.created_at.slice(0, 10)),
                name: c.created_by?.full_name ?? t('audit.system'),
              })}{' '}
              · {t('contracts.lastUpdated', { date: format.date(c.updated_at.slice(0, 10)) })}
            </p>
          </div>
          <div className="page-actions">
            {can(PERMISSIONS.contractArchive) && (
              <Button icon={archived ? <UndoOutlined /> : <InboxOutlined />} onClick={toggleArchive}>
                {archived ? t('contracts.restore') : t('contracts.archive')}
              </Button>
            )}
            {can(PERMISSIONS.contractEdit) && !archived && (
              <Button
                type="primary"
                icon={<EditOutlined />}
                onClick={() => navigate(`/contracts/${c.id}/edit`)}
              >
                {t('contracts.edit')}
              </Button>
            )}
          </div>
        </div>
        <dl className="contract-facts">
          <div>
            <dt>{t('contracts.startDate')}</dt>
            <dd>{format.date(c.start_date)}</dd>
          </div>
          <div>
            <dt>{t('contracts.endDate')}</dt>
            <dd>{c.end_date ? format.date(c.end_date) : t('contracts.openEnded')}</dd>
          </div>
          <div>
            <dt>{t('contracts.value')}</dt>
            <dd>
              <bdi dir="ltr">{format.money(c)}</bdi>
            </dd>
          </div>
          <div>
            <dt>{t('contracts.renewalDate')}</dt>
            <dd>{format.date(c.renewal_date)}</dd>
          </div>
        </dl>
        {progress && (
          <div className="term-progress">
            <span className="term-progress-label">{t('contracts.termProgress')}</span>
            <div
              className="term-progress-bar"
              role="progressbar"
              aria-valuenow={progress.percent}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <span style={{ width: `${progress.percent}%` }} />
            </div>
            <span className="person-email">
              {t('contracts.monthOf', { month: progress.month, months: progress.months })}
            </span>
          </div>
        )}
      </section>

      <div className="details-layout">
        <section className="panel">
          <h2 className="panel-title panel-gap">{t('contracts.summary')}</h2>
          {c.description ? (
            <p className="preserve-lines" dir="auto">
              {c.description}
            </p>
          ) : (
            <p className="muted">{t('contracts.noDescription')}</p>
          )}
        </section>

        <aside className="details-aside">
          <section className="panel">
            <h2 className="panel-title panel-gap">{t('contracts.partiesSection')}</h2>
            <ul className="side-list">
              {c.parties.map((party) => (
                <li key={party.id}>
                  <Link to={`/parties/${party.id}`} className="person">
                    <UserAvatar name={party.display_name} />
                    <span className="person-text">
                      <bdi className="person-name">{party.display_name}</bdi>
                      <span className="person-email">
                        {t(`partyTypes.${party.party_type}`)} · {t(`partyRoles.${party.role}`)}
                      </span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>

          <section className="panel">
            <h2 className="panel-title panel-gap">{t('contracts.properties')}</h2>
            {c.properties.length === 0 ? (
              <p className="muted">{t('contracts.noProperties')}</p>
            ) : (
              <ul className="side-list">
                {c.properties.map((prop) => (
                  <li key={prop.id} className="person-text">
                    <Link to={`/properties/${prop.id}`} className="person-name">
                      <bdi>{prop.name}</bdi>
                    </Link>
                    <span className="person-email">
                      {t(`propertyTypes.${prop.property_type}`)} · <span dir="ltr">{prop.code}</span>
                    </span>
                    <Link to={`/contracts?property=${prop.id}`} className="panel-link">
                      {t('contracts.allForProperty')}{' '}
                      <span className="arrow-forward" aria-hidden="true">
                        →
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <ActivityList contract={c} />
        </aside>
      </div>
    </div>
  )
}
