import { Select } from 'antd'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useUserDirectory, type UserSummary } from './api'

/** Choose an active user, e.g. who follows up an obligation (FR-OBL-03). */
export function UserSelect({
  value,
  onChange,
  placeholder,
  className,
  ariaLabel,
  known,
  enabled = true,
}: {
  value?: string | null
  onChange?: (id: string | null) => void
  placeholder?: string
  className?: string
  ariaLabel?: string
  /** Shown by name even when the search does not return it (the current assignee). */
  known?: Pick<UserSummary, 'id' | 'full_name'> | null
  /** The directory needs obligation:create or obligation:update. */
  enabled?: boolean
}) {
  const { t } = useTranslation()
  const [search, setSearch] = useState('')
  const users = useUserDirectory(search, enabled)
  const options = new Map(
    [...(known ? [known] : []), ...(users.data ?? [])].map((u) => [
      u.id,
      { value: u.id, label: u.full_name },
    ]),
  )
  return (
    <Select<string | null>
      showSearch
      allowClear
      filterOption={false}
      onSearch={setSearch}
      value={value ?? null}
      onChange={(id) => onChange?.(id ?? null)}
      options={[...options.values()]}
      loading={users.isFetching}
      placeholder={placeholder}
      notFoundContent={t('obligations.noUsersFound')}
      className={className}
      aria-label={ariaLabel}
    />
  )
}
