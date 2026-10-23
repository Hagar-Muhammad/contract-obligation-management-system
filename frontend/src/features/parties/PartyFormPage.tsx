import { App, Button, Form, Input, Segmented, Spin } from 'antd'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { PERMISSIONS, useAuth } from '../../auth/context'
import { PageHeader } from '../../components/PageHeader'
import { showServerErrors } from '../../components/showServerErrors'
import { useCreateParty, useParty, useUpdateParty, type PartyType } from './api'

interface PartyFormValues {
  party_type: PartyType
  display_name: string
  national_id?: string | null
  passport_no?: string | null
  registration_no?: string | null
  tax_no?: string | null
  email?: string | null
  phone?: string | null
  address?: string | null
  notes?: string | null
}

const TYPE_FIELDS: Record<PartyType, (keyof PartyFormValues)[]> = {
  individual: ['national_id', 'passport_no'],
  organization: ['registration_no', 'tax_no'],
}
const COMMON_FIELDS: (keyof PartyFormValues)[] = ['display_name', 'email', 'phone', 'address', 'notes']

/** Create (`/parties/new`), edit or view (`/parties/:id`) a party (FR-PARTY-01, FR-PARTY-02). */
export function PartyFormPage() {
  const { id } = useParams()
  const isNew = !id
  const { t } = useTranslation()
  const { message } = App.useApp()
  const { can } = useAuth()
  const navigate = useNavigate()
  const [form] = Form.useForm<PartyFormValues>()
  const existing = useParty(id)
  const create = useCreateParty()
  const update = useUpdateParty(id ?? '')
  const canManage = can(PERMISSIONS.partyManage)
  const partyType = Form.useWatch('party_type', form) ?? existing.data?.party_type ?? 'organization'

  useEffect(() => {
    if (existing.data) form.setFieldsValue(existing.data)
  }, [existing.data, form])

  const onFinish = async (values: PartyFormValues) => {
    // Send the fields of this party type only; empty inputs clear the value.
    const fields = [...COMMON_FIELDS, ...TYPE_FIELDS[partyType]]
    const body = Object.fromEntries(fields.map((field) => [field, values[field] || null]))
    try {
      if (isNew) {
        await create.mutateAsync({ ...body, party_type: partyType, display_name: values.display_name })
        message.success(t('parties.created'))
      } else {
        await update.mutateAsync(body)
        message.success(t('parties.saved'))
      }
      navigate('/parties')
    } catch (err) {
      showServerErrors(err, form, message, t)
    }
  }

  if (!isNew && existing.isLoading) return <Spin />

  const title = isNew ? t('parties.new') : canManage ? t('parties.edit') : t('parties.view')
  const saving = create.isPending || update.isPending

  return (
    <div className="page page-narrow">
      <PageHeader
        title={existing.data ? <bdi>{existing.data.display_name}</bdi> : title}
        subtitle={existing.data ? t(`partyTypes.${existing.data.party_type}`) : undefined}
        breadcrumb={[{ label: t('parties.title'), to: '/parties' }, { label: title }]}
      />
      <Form<PartyFormValues>
        form={form}
        layout="vertical"
        onFinish={onFinish}
        initialValues={{ party_type: 'organization' }}
        disabled={saving || !canManage}
      >
        <section className="panel form-section">
          <h2 className="form-section-title">
            <span className="step">1</span>
            {t('parties.identitySection')}
          </h2>
          {isNew && (
            <Form.Item label={t('parties.type')} name="party_type">
              <Segmented<PartyType>
                options={[
                  { value: 'organization', label: t('partyTypes.organization') },
                  { value: 'individual', label: t('partyTypes.individual') },
                ]}
              />
            </Form.Item>
          )}
          <Form.Item
            label={partyType === 'individual' ? t('parties.fullName') : t('parties.companyName')}
            name="display_name"
            rules={[{ required: true, whitespace: true, message: t('validation.required') }]}
          >
            <Input maxLength={300} />
          </Form.Item>
          {partyType === 'individual' ? (
            <div className="form-grid">
              <Form.Item label={t('parties.nationalId')} name="national_id">
                <Input maxLength={50} dir="ltr" />
              </Form.Item>
              <Form.Item label={t('parties.passportNo')} name="passport_no">
                <Input maxLength={50} dir="ltr" />
              </Form.Item>
            </div>
          ) : (
            <div className="form-grid">
              <Form.Item label={t('parties.registrationNo')} name="registration_no">
                <Input maxLength={50} dir="ltr" />
              </Form.Item>
              <Form.Item label={t('parties.taxNo')} name="tax_no">
                <Input maxLength={50} dir="ltr" />
              </Form.Item>
            </div>
          )}
        </section>

        <section className="panel form-section">
          <h2 className="form-section-title">
            <span className="step">2</span>
            {t('parties.contactSection')}
          </h2>
          <div className="form-grid">
            <Form.Item
              label={t('parties.email')}
              name="email"
              rules={[{ type: 'email', message: t('validation.email') }]}
            >
              <Input type="email" maxLength={320} dir="ltr" />
            </Form.Item>
            <Form.Item
              label={t('parties.phone')}
              name="phone"
              rules={[{ pattern: /^[0-9+()\-. /]+$/, message: t('validation.phone') }]}
            >
              <Input type="tel" maxLength={50} dir="ltr" />
            </Form.Item>
          </div>
          <Form.Item label={t('parties.address')} name="address">
            <Input.TextArea rows={2} maxLength={2000} />
          </Form.Item>
          <Form.Item label={t('parties.notes')} name="notes">
            <Input.TextArea rows={3} maxLength={2000} />
          </Form.Item>
        </section>

        {canManage && (
          <div className="panel form-actions">
            <Button onClick={() => navigate('/parties')}>{t('common.cancel')}</Button>
            <Button type="primary" htmlType="submit" loading={saving}>
              {t('common.save')}
            </Button>
          </div>
        )}
      </Form>
    </div>
  )
}
