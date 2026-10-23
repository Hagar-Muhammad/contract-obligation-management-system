import { Select } from 'antd'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParties, type Party } from '../parties/api'
import { useProperties, type Property } from '../properties/api'
import { useContracts } from './api'

const PICKER_SIZE = 20

interface PartySelectProps {
  /** `null` keeps the box empty after each pick (a search box rather than a field). */
  value?: string | null
  onChange?: (id: string | undefined, party?: Party) => void
  placeholder?: string
  /** Parties already chosen, left out of the options. */
  exclude?: string[]
  className?: string
  ariaLabel?: string
}

/** Search the party directory by name, e-mail, phone or ID number. */
export function PartySelect({
  value,
  onChange,
  placeholder,
  exclude = [],
  className,
  ariaLabel,
}: PartySelectProps) {
  const { t } = useTranslation()
  const [search, setSearch] = useState('')
  const parties = useParties({ page: 1, pageSize: PICKER_SIZE, q: search })
  const options = (parties.data?.items ?? [])
    .filter((party) => !exclude.includes(party.id))
    .map((party) => ({ value: party.id, label: party.display_name, party }))
  return (
    <Select<string | null, (typeof options)[number]>
      showSearch
      allowClear
      filterOption={false}
      onSearch={setSearch}
      value={value}
      onChange={(id, option) =>
        onChange?.(id ?? undefined, Array.isArray(option) ? undefined : option?.party)
      }
      options={options}
      loading={parties.isFetching}
      placeholder={placeholder}
      notFoundContent={t('contracts.noPartiesFound')}
      className={className}
      aria-label={ariaLabel}
    />
  )
}

interface PropertySelectProps {
  value?: string | string[]
  onChange?: (value: string | string[] | undefined) => void
  multiple?: boolean
  placeholder?: string
  className?: string
  ariaLabel?: string
  /** Properties to show by name even when the search does not return them (e.g. already linked). */
  known?: Pick<Property, 'id' | 'code' | 'name'>[]
}

/** Search the properties visible to the user by code, name, city or address. */
export function PropertySelect({
  value,
  onChange,
  multiple,
  placeholder,
  className,
  ariaLabel,
  known = [],
}: PropertySelectProps) {
  const { t } = useTranslation()
  const [search, setSearch] = useState('')
  const properties = useProperties({ page: 1, pageSize: PICKER_SIZE, q: search })
  const options = new Map(
    [...known, ...(properties.data?.items ?? [])].map((p) => [
      p.id,
      { value: p.id, label: `${p.code} · ${p.name}` },
    ]),
  )
  return (
    <Select<string | string[]>
      mode={multiple ? 'multiple' : undefined}
      showSearch
      allowClear
      filterOption={false}
      onSearch={setSearch}
      value={value}
      onChange={onChange}
      options={[...options.values()]}
      loading={properties.isFetching}
      placeholder={placeholder}
      notFoundContent={t('contracts.noPropertiesFound')}
      className={className}
      aria-label={ariaLabel}
    />
  )
}

interface ContractSelectProps {
  value?: string
  onChange?: (id: string | undefined) => void
  placeholder?: string
  className?: string
  ariaLabel?: string
  disabled?: boolean
  /** A contract to show by name even when the search does not return it (e.g. the preselected one). */
  known?: { id: string; contract_number: string; title: string }
}

/** Search the contracts visible to the user by number, title, party or property (archived ones left out). */
export function ContractSelect({
  value,
  onChange,
  placeholder,
  className,
  ariaLabel,
  disabled,
  known,
}: ContractSelectProps) {
  const { t } = useTranslation()
  const [search, setSearch] = useState('')
  const contracts = useContracts({ page: 1, pageSize: PICKER_SIZE, q: search })
  const options = new Map(
    [...(known ? [known] : []), ...(contracts.data?.items ?? [])].map((c) => [
      c.id,
      { value: c.id, label: `${c.contract_number} · ${c.title}` },
    ]),
  )
  return (
    <Select<string>
      showSearch
      allowClear
      filterOption={false}
      onSearch={setSearch}
      value={value}
      onChange={(id) => onChange?.(id ?? undefined)}
      options={[...options.values()]}
      loading={contracts.isFetching}
      placeholder={placeholder}
      notFoundContent={t('obligations.noContractsFound')}
      className={className}
      aria-label={ariaLabel}
      disabled={disabled}
    />
  )
}
