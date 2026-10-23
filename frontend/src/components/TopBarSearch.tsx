import { SearchOutlined } from '@ant-design/icons'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { AutoComplete, Input } from 'antd'
import { useEffect, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { unwrap } from '../api/errors'

const MIN_LENGTH = 2

function useDebounced(value: string, delayMs = 250) {
  const [settled, setSettled] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])
  return settled
}

/** Top-bar search from the design: contracts, parties, properties and obligations you can see (FR-SEARCH-01). */
export function TopBarSearch() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [text, setText] = useState('')
  const query = useDebounced(text.trim())
  const results = useQuery({
    queryKey: ['search', query],
    queryFn: async () =>
      unwrap(await api.GET('/api/v1/search', { params: { query: { q: query, limit: 5 } } })),
    enabled: query.length >= MIN_LENGTH,
    placeholderData: keepPreviousData,
  })
  const data = query.length >= MIN_LENGTH ? results.data : undefined

  const group = (key: string, label: string, items: { value: string; label: ReactNode }[]) =>
    items.length ? [{ key, label, options: items }] : []

  const options = data
    ? [
        ...group(
          'contracts',
          t('nav.contracts'),
          data.contracts.map((c) => ({
            value: `/contracts/${c.id}`,
            label: (
              <span className="search-hit">
                <bdi>{c.title}</bdi>{' '}
                <span className="search-hit-meta" dir="ltr">
                  {c.contract_number}
                </span>
              </span>
            ),
          })),
        ),
        ...group(
          'obligations',
          t('nav.obligations'),
          data.obligations.map((o) => ({
            value: `/obligations/${o.id}`,
            label: (
              <span className="search-hit">
                <bdi>{o.title}</bdi>{' '}
                <span className="search-hit-meta" dir="ltr">
                  {o.contract_number}
                </span>
              </span>
            ),
          })),
        ),
        ...group(
          'parties',
          t('nav.parties'),
          data.parties.map((p) => ({
            value: `/parties/${p.id}`,
            label: (
              <span className="search-hit">
                <bdi>{p.display_name}</bdi>{' '}
                <span className="search-hit-meta">{t(`partyTypes.${p.party_type}`)}</span>
              </span>
            ),
          })),
        ),
        ...group(
          'properties',
          t('nav.properties'),
          data.properties.map((p) => ({
            value: `/properties/${p.id}`,
            label: (
              <span className="search-hit">
                <bdi>{p.name}</bdi>{' '}
                <span className="search-hit-meta" dir="ltr">
                  {p.code}
                </span>
              </span>
            ),
          })),
        ),
        {
          key: 'all',
          label: '',
          options: [
            {
              value: `/contracts?q=${encodeURIComponent(query)}`,
              label: <span className="search-all">{t('search.allContracts', { query })}</span>,
            },
          ],
        },
      ]
    : []

  return (
    <AutoComplete
      className="topbar-search"
      value={text}
      options={options}
      onChange={setText}
      onSelect={(path: string) => {
        setText('')
        navigate(path)
      }}
      notFoundContent={data ? t('search.nothing') : undefined}
      popupMatchSelectWidth={420}
    >
      <Input
        prefix={<SearchOutlined />}
        placeholder={t('search.placeholder')}
        aria-label={t('search.placeholder')}
        allowClear
      />
    </AutoComplete>
  )
}
