import { useTranslation } from 'react-i18next'
import { FILE_TYPE_EXTENSIONS, useUploadLimits } from './api'

/**
 * Quick check before uploading: allowed extension and size (decision D-12). The server checks the real content
 * type and the size again; this only saves the user a wait for an upload that would be refused.
 */
export function useFileCheck() {
  const { t } = useTranslation()
  const limits = useUploadLimits()
  const types = limits.data?.allowed_types ?? []
  const maxMb = Math.round((limits.data?.max_bytes ?? 0) / (1024 * 1024))
  const names = types.map((type) => type.toUpperCase()).join(', ')

  const check = (file: File): string | undefined => {
    const name = file.name.toLowerCase()
    if (!types.some((type) => FILE_TYPE_EXTENSIONS[type].some((ext) => name.endsWith(ext)))) {
      return t('documents.wrongType', { types: names })
    }
    if (limits.data && file.size > limits.data.max_bytes) return t('documents.tooLarge', { max: maxMb })
    if (file.size === 0) return t('documents.empty')
    return undefined
  }
  check.hint = t('documents.hint', { types: names, max: maxMb })
  return check
}
