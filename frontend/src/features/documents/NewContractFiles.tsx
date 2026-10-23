import { UploadOutlined } from '@ant-design/icons'
import { Alert, Upload } from 'antd'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { FILE_TYPE_EXTENSIONS, useUploadLimits } from './api'
import { useFileCheck } from './useFileCheck'

/**
 * New contract, section 4 (design screen 5): the signed copy and other files, uploaded once the contract exists
 * (a document always belongs to a contract, BR-09).
 */
export function NewContractFiles({
  value,
  onChange,
}: {
  value: File[]
  /** Receives an update function, so several files dropped at once are all kept (e.g. a state setter). */
  onChange: (update: (files: File[]) => File[]) => void
}) {
  const { t } = useTranslation()
  const limits = useUploadLimits()
  const check = useFileCheck()
  const [error, setError] = useState<string>()
  const accept = (limits.data?.allowed_types ?? []).flatMap((type) => FILE_TYPE_EXTENSIONS[type]).join(',')

  return (
    <div className="new-contract-files">
      <Upload.Dragger
        accept={accept}
        multiple
        fileList={value.map((file, index) => ({
          uid: `${index}-${file.name}`,
          name: file.name,
          status: 'done',
        }))}
        beforeUpload={(file) => {
          const problem = check(file)
          setError(problem)
          if (!problem) onChange((files) => [...files, file])
          return false // uploaded after the contract is created
        }}
        onRemove={(removed) =>
          onChange((files) => files.filter((file, index) => `${index}-${file.name}` !== removed.uid))
        }
      >
        <p className="ant-upload-drag-icon">
          <UploadOutlined />
        </p>
        <p className="ant-upload-text">{t('documents.dropSigned')}</p>
        <p className="ant-upload-hint">{check.hint}</p>
      </Upload.Dragger>
      {error && <Alert type="error" showIcon className="upload-error" message={error} />}
      <p className="muted form-note">{t('documents.afterSaving')}</p>
    </div>
  )
}
