import { Spin } from 'antd'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useObligations } from './api'
import { useObligationFormat } from './useObligationFormat'

const SHOWN = 5

/** Contract page, "Open obligations" (design screen 4; SRS 9.3: the contract shows its obligations). */
export function ContractObligations({ contractId }: { contractId: string }) {
  const { t } = useTranslation()
  const format = useObligationFormat()
  const open = useObligations({ page: 1, pageSize: SHOWN, view: 'open', contractId, sort: 'due_date' })
  const total = open.data?.total ?? 0

  return (
    <section className="panel panel-flush">
      <div className="panel-header panel-pad">
        <h2 className="panel-title">{t('obligations.openOnContract')}</h2>
        {total > 0 && (
          <Link to={`/obligations?contract=${contractId}`} className="panel-link-inline">
            {t('obligations.viewAll', { count: total })}{' '}
            <span className="arrow-forward" aria-hidden="true">
              →
            </span>
          </Link>
        )}
      </div>
      {open.isLoading ? (
        <Spin />
      ) : total === 0 ? (
        <p className="muted panel-pad">{t('obligations.noneOpen')}</p>
      ) : (
        <ul className="obligation-rows">
          {open.data!.items.map((o) => {
            const due = format.due(o)
            const status = format.status(o)
            return (
              <li key={o.id} className={due.late ? 'is-late' : undefined}>
                <Link to={`/obligations/${o.id}`} className="obligation-row">
                  <span className="person-text obligation-row-main">
                    <bdi className="person-name">{o.title}</bdi>
                    <span className="person-email">
                      <bdi>{o.responsible_party.display_name}</bdi>
                      {o.responsible_user && (
                        <>
                          {' · '}
                          <bdi>{o.responsible_user.full_name}</bdi>
                        </>
                      )}
                      {' · '}
                      {format.repeats(o.recurrence_rule)}
                    </span>
                  </span>
                  <span className={`person-text obligation-row-due ${due.late ? 'text-danger' : ''}`}>
                    <strong>{due.date}</strong>
                    {due.note && <span className={due.late ? '' : 'person-email'}>{due.note}</span>}
                  </span>
                  <span className={status.className}>{status.label}</span>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
      {total > SHOWN && (
        <p className="muted panel-pad more-note">{t('obligations.more', { count: total - SHOWN })}</p>
      )}
    </section>
  )
}
