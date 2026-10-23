import { DownloadOutlined, InboxOutlined, UploadOutlined } from '@ant-design/icons'
import { Alert, App, Button, Form, Modal, Select, Spin, Upload } from 'antd'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../api/errors'
import { PERMISSIONS, useAuth } from '../../auth/context'
import { useLanguage } from '../../i18n/useLanguage'
import { useContractFormat } from '../contracts/useContractFormat'
import {
  DOCUMENT_KINDS,
  FILE_TYPE_EXTENSIONS,
  saveDocument,
  useContractDocuments,
  useUploadDocument,
  useUploadLimits,
  viewDocument,
  type ContractDocument,
  type DocumentKind,
} from './api'
import { useFileCheck } from './useFileCheck'

const VIEWABLE = new Set(['pdf', 'png', 'jpg'])

function useBytes() {
  const { language } = useLanguage()
  const { t } = useTranslation()
  const number = new Intl.NumberFormat(language, { maximumFractionDigits: 1 })
  return (bytes: number) =>
    bytes >= 1024 * 1024
      ? t('documents.megabytes', { value: number.format(bytes / (1024 * 1024)) })
      : t('documents.kilobytes', { value: number.format(Math.max(bytes / 1024, 0.1)) })
}

function UploadDialog({
  contractId,
  open,
  onClose,
}: {
  contractId: string
  open: boolean
  onClose: () => void
}) {
  const { t } = useTranslation()
  const { message } = App.useApp()
  const limits = useUploadLimits()
  const check = useFileCheck()
  const upload = useUploadDocument(contractId)
  const [file, setFile] = useState<File>()
  const [kind, setKind] = useState<DocumentKind>('contract')
  const [error, setError] = useState<string>()
  const accept = (limits.data?.allowed_types ?? []).flatMap((type) => FILE_TYPE_EXTENSIONS[type]).join(',')

  const close = () => {
    setFile(undefined)
    setError(undefined)
    onClose()
  }

  const submit = async () => {
    if (!file) return setError(t('documents.chooseFile'))
    try {
      await upload.mutateAsync({ file, kind })
      message.success(t('documents.uploaded', { name: file.name }))
      close()
    } catch (err) {
      if (!(err instanceof ApiError)) throw err
      setError(err.message)
    }
  }

  return (
    <Modal
      open={open}
      title={t('documents.uploadTitle')}
      okText={t('documents.upload')}
      cancelText={t('common.cancel')}
      onOk={submit}
      onCancel={close}
      confirmLoading={upload.isPending}
      okButtonProps={{ disabled: !file }}
      destroyOnHidden
    >
      <Form layout="vertical">
        <Form.Item label={t('documents.kind')}>
          <Select<DocumentKind>
            value={kind}
            onChange={setKind}
            aria-label={t('documents.kind')}
            options={DOCUMENT_KINDS.map((value) => ({ value, label: t(`documents.kinds.${value}`) }))}
          />
        </Form.Item>
        <Upload.Dragger
          accept={accept}
          multiple={false}
          maxCount={1}
          showUploadList={file ? { showRemoveIcon: true } : false}
          fileList={file ? [{ uid: 'chosen', name: file.name, status: 'done' }] : []}
          beforeUpload={(chosen) => {
            const problem = check(chosen)
            setError(problem)
            setFile(problem ? undefined : chosen)
            return false // upload on OK, not on drop
          }}
          onRemove={() => setFile(undefined)}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">{t('documents.dropHere')}</p>
          <p className="ant-upload-hint">{check.hint}</p>
        </Upload.Dragger>
        {error && <Alert type="error" showIcon className="upload-error" message={error} />}
      </Form>
    </Modal>
  )
}

/** The contract's documents (design screen 4; FR-DOC-01, FR-DOC-03, FR-DOC-05). */
export function DocumentsPanel({ contractId, readOnly }: { contractId: string; readOnly: boolean }) {
  const { t } = useTranslation()
  const { can } = useAuth()
  const { message } = App.useApp()
  const format = useContractFormat()
  const bytes = useBytes()
  const documents = useContractDocuments(contractId)
  const [uploading, setUploading] = useState(false)

  const run =
    (action: (document: ContractDocument) => Promise<void>) => async (document: ContractDocument) => {
      try {
        await action(document)
      } catch {
        message.error(t('documents.downloadFailed'))
      }
    }
  const open = run((document) =>
    VIEWABLE.has(document.file_type) ? viewDocument(document) : saveDocument(document),
  )
  const download = run(saveDocument)

  return (
    <section className="panel">
      <div className="panel-header">
        <h2 className="panel-title">{t('documents.title')}</h2>
        {can(PERMISSIONS.documentUpload) && !readOnly && (
          <Button icon={<UploadOutlined />} onClick={() => setUploading(true)}>
            {t('documents.upload')}
          </Button>
        )}
      </div>
      {documents.isLoading ? (
        <Spin />
      ) : !documents.data?.length ? (
        <p className="muted">{t('documents.none')}</p>
      ) : (
        <ul className="document-list">
          {documents.data.map((document) => (
            <li key={document.id} className="document-row">
              <span className={`file-badge file-${document.file_type}`} aria-hidden="true">
                {document.file_type.toUpperCase()}
              </span>
              <span className="person-text document-text">
                <button type="button" className="link-text" onClick={() => open(document)}>
                  <bdi>{document.original_filename}</bdi>
                </button>
                <span className="person-email">
                  {bytes(document.size_bytes)} · {t(`documents.kinds.${document.kind}`)} ·{' '}
                  {format.date(document.uploaded_at.slice(0, 10))}
                </span>
              </span>
              <Button
                type="text"
                icon={<DownloadOutlined />}
                aria-label={t('documents.downloadName', { name: document.original_filename })}
                onClick={() => download(document)}
              />
            </li>
          ))}
        </ul>
      )}
      <UploadDialog contractId={contractId} open={uploading} onClose={() => setUploading(false)} />
    </section>
  )
}
