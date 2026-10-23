import { App, Button, Form, Input, InputNumber, Select, Spin } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { PERMISSIONS, useAuth } from '../../auth/context'
import { PageHeader } from '../../components/PageHeader'
import { showServerErrors } from '../../components/showServerErrors'
import {
  PROPERTY_TYPES,
  useAssignableManagers,
  useCreateProperty,
  useProperty,
  useUpdateProperty,
  type PropertyType,
} from './api'

interface PropertyFormValues {
  code: string
  name: string
  property_type: PropertyType
  area_sqm?: number | null
  address?: string | null
  city?: string | null
  country?: string | null
  notes?: string | null
  manager_ids: string[]
}

/** Create (`/properties/new`), edit or view (`/properties/:id`) a property and its assigned managers. */
export function PropertyFormPage() {
  const { id } = useParams()
  const isNew = !id
  const { t } = useTranslation()
  const { message } = App.useApp()
  const { can } = useAuth()
  const navigate = useNavigate()
  const [form] = Form.useForm<PropertyFormValues>()
  const canManage = can(PERMISSIONS.propertyManage)
  const [managerSearch, setManagerSearch] = useState('')
  const existing = useProperty(id)
  const assignable = useAssignableManagers(managerSearch, canManage)
  const create = useCreateProperty()
  const update = useUpdateProperty(id ?? '')

  useEffect(() => {
    if (existing.data) {
      const { managers, area_sqm, ...rest } = existing.data
      form.setFieldsValue({
        ...rest,
        area_sqm: area_sqm === null || area_sqm === undefined ? null : Number(area_sqm),
        manager_ids: managers.map((m) => m.id),
      })
    }
  }, [existing.data, form])

  const onFinish = async (values: PropertyFormValues) => {
    const body = {
      code: values.code,
      name: values.name,
      property_type: values.property_type,
      area_sqm: values.area_sqm ?? null,
      address: values.address || null,
      city: values.city || null,
      country: values.country || null,
      notes: values.notes || null,
      manager_ids: values.manager_ids,
    }
    try {
      if (isNew) {
        await create.mutateAsync(body)
        message.success(t('properties.created'))
      } else {
        await update.mutateAsync(body)
        message.success(t('properties.saved'))
      }
      navigate('/properties')
    } catch (err) {
      showServerErrors(err, form, message, t)
    }
  }

  if (!isNew && existing.isLoading) return <Spin />

  const title = isNew ? t('properties.new') : canManage ? t('properties.edit') : t('properties.view')
  const saving = create.isPending || update.isPending
  // Current managers stay selectable even when the search does not return them.
  const managerOptions = new Map(
    [...(existing.data?.managers ?? []), ...(assignable.data ?? [])].map((m) => [
      m.id,
      { value: m.id, label: `${m.full_name} · ${m.email}` },
    ]),
  )

  return (
    <div className="page page-narrow">
      <PageHeader
        title={existing.data ? <bdi>{existing.data.name}</bdi> : title}
        subtitle={existing.data?.code}
        actions={
          existing.data && (
            <span className="page-actions">
              <Link to={`/contracts?property=${existing.data.id}`}>
                <Button>{t('properties.contracts')}</Button>
              </Link>
              <Link to={`/obligations?property=${existing.data.id}`}>
                <Button>{t('properties.obligations')}</Button>
              </Link>
            </span>
          )
        }
        breadcrumb={[{ label: t('properties.title'), to: '/properties' }, { label: title }]}
      />
      <Form<PropertyFormValues>
        form={form}
        layout="vertical"
        onFinish={onFinish}
        initialValues={{ manager_ids: [] }}
        disabled={saving || !canManage}
      >
        <section className="panel form-section">
          <h2 className="form-section-title">
            <span className="step">1</span>
            {t('properties.detailsSection')}
          </h2>
          <div className="form-grid">
            <Form.Item
              label={t('properties.code')}
              name="code"
              extra={t('properties.codeHelp')}
              normalize={(value: string) => value.toUpperCase()}
              rules={[
                { required: true, whitespace: true, message: t('validation.required') },
                { pattern: /^[A-Z0-9][A-Z0-9 ._/-]*$/, message: t('properties.codeFormat') },
              ]}
            >
              <Input maxLength={50} dir="ltr" />
            </Form.Item>
            <Form.Item
              label={t('properties.type')}
              name="property_type"
              rules={[{ required: true, message: t('validation.required') }]}
            >
              <Select<PropertyType>
                options={PROPERTY_TYPES.map((value) => ({ value, label: t(`propertyTypes.${value}`) }))}
              />
            </Form.Item>
          </div>
          <Form.Item
            label={t('properties.name')}
            name="name"
            rules={[{ required: true, whitespace: true, message: t('validation.required') }]}
          >
            <Input maxLength={200} />
          </Form.Item>
          <Form.Item label={t('properties.area')} name="area_sqm" className="form-narrow">
            <InputNumber<number>
              min={0.01}
              max={9999999999.99}
              precision={2}
              suffix="m²"
              style={{ width: '100%' }}
            />
          </Form.Item>
        </section>

        <section className="panel form-section">
          <h2 className="form-section-title">
            <span className="step">2</span>
            {t('properties.locationSection')}
          </h2>
          <Form.Item label={t('properties.address')} name="address">
            <Input.TextArea rows={2} maxLength={2000} />
          </Form.Item>
          <div className="form-grid">
            <Form.Item label={t('properties.city')} name="city">
              <Input maxLength={100} />
            </Form.Item>
            <Form.Item label={t('properties.country')} name="country">
              <Input maxLength={100} />
            </Form.Item>
          </div>
        </section>

        <section className="panel form-section">
          <h2 className="form-section-title">
            <span className="step">3</span>
            {t('properties.managersSection')}
          </h2>
          <Form.Item label={t('properties.managers')} name="manager_ids" extra={t('properties.managersHelp')}>
            <Select<string[]>
              mode="multiple"
              showSearch
              filterOption={false}
              onSearch={setManagerSearch}
              loading={assignable.isFetching}
              options={[...managerOptions.values()]}
              notFoundContent={t('properties.noManagers')}
            />
          </Form.Item>
          <Form.Item label={t('properties.notes')} name="notes">
            <Input.TextArea rows={3} maxLength={2000} />
          </Form.Item>
        </section>

        {canManage && (
          <div className="panel form-actions">
            <Button onClick={() => navigate('/properties')}>{t('common.cancel')}</Button>
            <Button type="primary" htmlType="submit" loading={saving}>
              {t('common.save')}
            </Button>
          </div>
        )}
      </Form>
    </div>
  )
}
