import { CloseOutlined, EditOutlined, PaperClipOutlined } from '@ant-design/icons'
import { Alert, App, Button, Input, Segmented, Spin, Upload } from 'antd'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { ApiError } from '../../api/errors'
import { PERMISSIONS, useAuth } from '../../auth/context'
import { useRelativeTime } from '../../i18n/useRelativeTime'
import { saveDocument, viewDocument, type ContractDocument } from '../documents/api'
import { useFileCheck } from '../documents/useFileCheck'
import {
  STATUSES,
  useAddEvidence,
  useChangeStatus,
  useObligation,
  useObligationActivity,
  useObligationEvidence,
  type ObligationStatus,
} from './api'
import { useObligationFormat } from './useObligationFormat'

const VIEWABLE = new Set(['pdf', 'png', 'jpg'])

function Activity({ obligationId }: { obligationId: string }) {
  const { t } = useTranslation()
  const relativeTime = useRelativeTime()
  const activity = useObligationActivity(obligationId)
  if (!activity.data?.length) return null
  return (
    <div className="panel-block">
      <h3 className="panel-label">{t('obligations.history')}</h3>
      <ul className="activity-list">
        {activity.data.slice(0, 5).map((entry, index) => {
          const [from, to] = entry.changes?.status ?? []
          const note = entry.changes?.note?.[1] as string | undefined
          return (
            <li key={`${entry.occurred_at}-${index}`} className="activity-item tone-dot-grey">
              <span>
                <strong>
                  <bdi>{entry.actor?.full_name ?? t('audit.system')}</bdi>
                </strong>{' '}
                {entry.action === 'obligation.status_changed' && from
                  ? t('obligations.activity.statusChanged', {
                      from: t(`obligations.statuses.${String(from)}`),
                      to: t(`obligations.statuses.${String(to)}`),
                    })
                  : t(`obligations.activity.${entry.action.split('.')[1]}`)}
              </span>
              {note && <span className="activity-note">“{String(note)}”</span>}
              <span className="person-email">{relativeTime(entry.occurred_at)}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

/** The selected obligation, beside the list (design screen 7): details, status update, evidence, note. */
export function ObligationPanel({ obligationId, onClose }: { obligationId: string; onClose: () => void }) {
  const { t } = useTranslation()
  const { can, user } = useAuth()
  const { message } = App.useApp()
  const format = useObligationFormat()
  const check = useFileCheck()
  const obligation = useObligation(obligationId)
  const evidence = useObligationEvidence(obligationId, can(PERMISSIONS.documentView))
  const changeStatus = useChangeStatus(obligationId)
  const addEvidence = useAddEvidence(obligationId)
  const [chosen, setChosen] = useState<ObligationStatus>()
  const [note, setNote] = useState('')
  const [error, setError] = useState<string>()

  if (obligation.isLoading)
    return (
      <aside className="panel obligation-panel">
        <Spin />
      </aside>
    )
  const o = obligation.data
  if (!o) return null

  const status = format.status(o)
  const due = format.due(o)
  // Archived contracts refuse changes on the server; that message is shown below.
  const canUpdate = can(PERMISSIONS.obligationUpdate)
  const canEditDetails = canUpdate && !user?.data_scopes.every((scope) => scope === 'assigned_obligations')
  const selected = chosen ?? o.status
  const dirty = selected !== o.status || note.trim() !== ''

  const save = async () => {
    setError(undefined)
    try {
      await changeStatus.mutateAsync({ status: selected, note: note.trim() || null })
      message.success(t('obligations.updated'))
      setChosen(undefined)
      setNote('')
    } catch (err) {
      if (!(err instanceof ApiError)) throw err
      setError(err.message)
    }
  }

  const attach = async (file: File) => {
    const problem = check(file)
    if (problem) return setError(problem)
    setError(undefined)
    try {
      await addEvidence.mutateAsync(file)
      message.success(t('documents.uploaded', { name: file.name }))
    } catch (err) {
      if (!(err instanceof ApiError)) throw err
      setError(err.message)
    }
  }

  const open = async (document: ContractDocument) => {
    try {
      await (VIEWABLE.has(document.file_type) ? viewDocument(document) : saveDocument(document))
    } catch {
      message.error(t('documents.downloadFailed'))
    }
  }

  return (
    <aside className="panel obligation-panel" aria-label={t('obligations.details')}>
      <div className="obligation-panel-top">
        <span className="person-text">
          <span className={status.className}>
            {status.label}
            {due.late && due.note ? ` · ${due.note}` : ''}
          </span>
        </span>
        <Button type="text" icon={<CloseOutlined />} aria-label={t('common.close')} onClick={onClose} />
      </div>
      <h2 className="obligation-title">
        <bdi>{o.title}</bdi>
      </h2>
      <Link to={`/contracts/${o.contract.id}`} className="contract-link">
        <bdi dir="ltr">{o.contract.contract_number}</bdi> · <bdi>{o.contract.title}</bdi>
      </Link>

      <dl className="fact-grid">
        <div>
          <dt>{t('obligations.party')}</dt>
          <dd>
            <bdi>{o.responsible_party.display_name}</bdi>
          </dd>
        </div>
        <div>
          <dt>{t('obligations.owner')}</dt>
          <dd>{o.responsible_user ? <bdi>{o.responsible_user.full_name}</bdi> : '—'}</dd>
        </div>
        <div>
          <dt>{t('obligations.due')}</dt>
          <dd className={due.late ? 'text-danger' : undefined}>{due.date}</dd>
        </div>
        <div>
          <dt>{t('obligations.repeats')}</dt>
          <dd>{format.repeats(o.recurrence_rule)}</dd>
        </div>
      </dl>
      <div className="panel-block">
        <h3 className="panel-label">{t('obligations.description')}</h3>
        <p className="preserve-lines" dir="auto">
          {o.description}
        </p>
        {o.penalty_text && (
          <p className="muted preserve-lines" dir="auto">
            {t('obligations.penalty')}: {o.penalty_text}
          </p>
        )}
      </div>

      {canUpdate && (
        <div className="panel-block">
          <h3 className="panel-label">{t('obligations.updateStatus')}</h3>
          <Segmented<ObligationStatus>
            block
            value={selected}
            onChange={setChosen}
            options={STATUSES.map((value) => ({ value, label: t(`obligations.statuses.${value}`) }))}
          />
          <p className="form-note muted">{t('obligations.overdueHelp')}</p>
          <Upload
            showUploadList={false}
            beforeUpload={(file) => {
              void attach(file)
              return false
            }}
          >
            <Button
              icon={<PaperClipOutlined />}
              block
              className="evidence-button"
              loading={addEvidence.isPending}
            >
              {t('obligations.attachEvidence')}
            </Button>
          </Upload>
          <label className="panel-label" htmlFor="obligation-note">
            {t('obligations.note')}
          </label>
          <Input.TextArea
            id="obligation-note"
            rows={3}
            maxLength={1000}
            value={note}
            placeholder={t('obligations.notePlaceholder')}
            onChange={(e) => setNote(e.target.value)}
          />
          {error && <Alert type="error" showIcon className="upload-error" message={error} />}
          <Button
            type="primary"
            block
            className="save-update"
            disabled={!dirty}
            loading={changeStatus.isPending}
            onClick={save}
          >
            {t('obligations.saveUpdate')}
          </Button>
        </div>
      )}

      {(evidence.data?.length ?? 0) > 0 && (
        <div className="panel-block">
          <h3 className="panel-label">{t('obligations.evidence')}</h3>
          <ul className="side-list">
            {evidence.data!.map((document) => (
              <li key={document.id}>
                <button type="button" className="link-text" onClick={() => open(document)}>
                  <PaperClipOutlined /> <bdi>{document.original_filename}</bdi>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <Activity obligationId={o.id} />

      {canEditDetails && (
        <Link to={`/obligations/${o.id}/edit`}>
          <Button icon={<EditOutlined />} block>
            {t('obligations.editDetails')}
          </Button>
        </Link>
      )}
    </aside>
  )
}
