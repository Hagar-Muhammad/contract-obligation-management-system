import { PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { Button, Input, Select, Table, type TableProps } from 'antd'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { PERMISSIONS, useAuth } from '../../auth/context'
import { PageHeader } from '../../components/PageHeader'
import { UserAvatar } from '../../components/UserAvatar'
import { useListSearch } from '../../components/useListSearch'
import { useLanguage } from '../../i18n/useLanguage'
import { PROPERTY_TYPES, useProperties, type Property, type PropertyType } from './api'

const PAGE_SIZE = 25

/** Properties (SRS 4.6): the real estate that contracts relate to, and who manages each one. */
export function PropertiesPage() {
  const { t } = useTranslation()
  const { language } = useLanguage()
  const { can, user } = useAuth()
  const { search, setSearch, query, page, setPage } = useListSearch()
  const [propertyType, setPropertyType] = useState<PropertyType>()
  const properties = useProperties({ page, pageSize: PAGE_SIZE, q: query, propertyType })
  const canManage = can(PERMISSIONS.propertyManage)
  const area = new Intl.NumberFormat(language, { maximumFractionDigits: 2 })
  const scopes = user?.data_scopes ?? []
  // Mirrors the backend rule (properties/service.py) to explain an empty list.
  const emptyKey = scopes.includes('all')
    ? 'properties.empty'
    : scopes.includes('assigned_properties')
      ? 'properties.emptyAssigned'
      : 'properties.emptyScoped'

  const columns: TableProps<Property>['columns'] = [
    {
      title: t('properties.colProperty'),
      dataIndex: 'name',
      render: (_, prop) => (
        <Link to={`/properties/${prop.id}`} className="person-text">
          <bdi className="person-name">{prop.name}</bdi>
          <span className="person-email" dir="ltr">
            {prop.code}
          </span>
        </Link>
      ),
    },
    {
      title: t('properties.colType'),
      dataIndex: 'property_type',
      render: (value: PropertyType) => <span className="pill pill-grey">{t(`propertyTypes.${value}`)}</span>,
    },
    {
      title: t('properties.colLocation'),
      key: 'location',
      render: (_, prop) => [prop.city, prop.country].filter(Boolean).join(', ') || '—',
    },
    {
      title: t('properties.colArea'),
      dataIndex: 'area_sqm',
      align: 'end',
      render: (value: string | number | null) =>
        value === null ? '—' : t('properties.areaValue', { value: area.format(Number(value)) }),
    },
    {
      title: t('properties.colManagers'),
      dataIndex: 'managers',
      render: (managers: Property['managers']) =>
        managers.length ? (
          <span className="manager-list">
            {managers.map((m) => (
              <span key={m.id} className="manager-chip">
                <UserAvatar name={m.full_name} size={24} />
                <bdi>{m.full_name}</bdi>
              </span>
            ))}
          </span>
        ) : (
          <span className="pill pill-amber">{t('properties.unassigned')}</span>
        ),
    },
  ]

  return (
    <div className="page">
      <PageHeader
        title={t('properties.title')}
        subtitle={t('properties.subtitle')}
        actions={
          canManage && (
            <Link to="/properties/new">
              <Button type="primary" icon={<PlusOutlined />}>
                {t('properties.add')}
              </Button>
            </Link>
          )
        }
      />
      <section className="panel panel-flush">
        <div className="panel-toolbar list-toolbar">
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder={t('properties.search')}
            aria-label={t('properties.search')}
            className="search-box"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Select<PropertyType>
            allowClear
            className="list-filter"
            placeholder={t('properties.allTypes')}
            aria-label={t('properties.typeFilter')}
            value={propertyType}
            onChange={(value) => {
              setPropertyType(value)
              setPage(1)
            }}
            options={PROPERTY_TYPES.map((value) => ({ value, label: t(`propertyTypes.${value}`) }))}
          />
        </div>
        <Table<Property>
          rowKey="id"
          columns={columns}
          dataSource={properties.data?.items}
          loading={properties.isFetching}
          scroll={{ x: 860 }}
          locale={{ emptyText: t(emptyKey) }}
          pagination={{
            current: page,
            pageSize: PAGE_SIZE,
            total: properties.data?.total ?? 0,
            showSizeChanger: false,
            hideOnSinglePage: true,
            onChange: setPage,
          }}
        />
      </section>
    </div>
  )
}
