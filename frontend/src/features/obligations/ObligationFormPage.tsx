import { App, Button, Checkbox, DatePicker, Form, Input, Segmented, Select, Spin } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { PageHeader } from '../../components/PageHeader'
import { showServerErrors } from '../../components/showServerErrors'
import { useContract } from '../contracts/api'
import { ContractSelect } from '../contracts/pickers'
import {
  PRIORITIES,
  useCreateObligation,
  useObligation,
  useUpdateObligation,
  type ObligationStatus,
  type Priority,
} from './api'
import { REPEAT_PRESETS, presetOf, type RepeatPreset } from './useObligationFormat'
import { UserSelect } from './UserSelect'

const DAY = 'YYYY-MM-DD'

interface ObligationFormValues {
  contract_id?: string
  title: string
  description: string
  responsible_party_id?: string
  responsible_user_id?: string | null
  start_date?: Dayjs | null
  due_date?: Dayjs | null
  ongoing: boolean
  priority: Priority
  status: ObligationStatus
  repeat: RepeatPreset | 'none' | 'custom'
  custom_rule?: string
  penalty_text?: string
  notes?: string
}

const day = (value: Dayjs | null | undefined) => (value ? value.format(DAY) : null)

/** New obligation (`/obligations/new?contract=…`) and edit (`/obligations/:id/edit`): FR-OBL-01..03, FR-OBL-06. */
export function ObligationFormPage() {
  const { id } = useParams()
  const isNew = !id
  const [searchParams] = useSearchParams()
  const { t } = useTranslation()
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [form] = Form.useForm<ObligationFormValues>()
  const existing = useObligation(id)
  const contractId = Form.useWatch('contract_id', form) ?? existing.data?.contract.id
  const contract = useContract(contractId)
  const create = useCreateObligation()
  const update = useUpdateObligation(id ?? '')
  const ongoing = Form.useWatch('ongoing', form)
  const repeat = Form.useWatch('repeat', form)

  useEffect(() => {
    const preset = searchParams.get('contract')
    if (isNew && preset) form.setFieldsValue({ contract_id: preset })
  }, [isNew, searchParams, form])

  useEffect(() => {
    const o = existing.data
    if (!o) return
    const preset = presetOf(o.recurrence_rule)
    form.setFieldsValue({
      contract_id: o.contract.id,
      title: o.title,
      description: o.description,
      responsible_party_id: o.responsible_party.id,
      responsible_user_id: o.responsible_user?.id ?? null,
      start_date: o.start_date ? dayjs(o.start_date) : null,
      due_date: o.due_date ? dayjs(o.due_date) : null,
      ongoing: !o.due_date,
      priority: o.priority,
      repeat: preset,
      custom_rule: preset === 'custom' ? (o.recurrence_rule ?? undefined) : undefined,
      penalty_text: o.penalty_text ?? undefined,
      notes: o.notes ?? undefined,
    })
  }, [existing.data, form])

  const onFinish = async (values: ObligationFormValues) => {
    const rule =
      values.repeat === 'none'
        ? null
        : values.repeat === 'custom'
          ? values.custom_rule?.trim() || null
          : REPEAT_PRESETS[values.repeat]
    const details = {
      title: values.title,
      description: values.description,
      responsible_party_id: values.responsible_party_id!,
      responsible_user_id: values.responsible_user_id ?? null,
      start_date: day(values.start_date),
      due_date: values.ongoing ? null : day(values.due_date),
      priority: values.priority,
      recurrence_rule: values.ongoing ? null : rule,
      penalty_text: values.penalty_text || null,
      notes: values.notes || null,
    }
    try {
      const saved = isNew
        ? await create.mutateAsync({ ...details, contract_id: values.contract_id!, status: values.status })
        : await update.mutateAsync(details)
      message.success(isNew ? t('obligations.created') : t('obligations.saved'))
      navigate(`/obligations/${saved.id}`)
    } catch (err) {
      showServerErrors(err, form, message, t)
    }
  }

  if (!isNew && existing.isLoading) return <Spin />
  const title = isNew ? t('obligations.new') : t('obligations.edit')
  const saving = create.isPending || update.isPending
  const partyOptions = (contract.data?.parties ?? []).map((party) => ({
    value: party.id,
    label: `${party.display_name} · ${t(`partyRoles.${party.role}`)}`,
  }))

  return (
    <div className="page page-narrow">
      <PageHeader
        title={existing.data ? <bdi>{existing.data.title}</bdi> : title}
        breadcrumb={[{ label: t('obligations.title'), to: '/obligations' }, { label: title }]}
      />
      <Form<ObligationFormValues>
        form={form}
        layout="vertical"
        onFinish={onFinish}
        disabled={saving}
        initialValues={{ priority: 'medium', status: 'pending', repeat: 'none', ongoing: false }}
      >
        <section className="panel form-section">
          <h2 className="form-section-title">
            <span className="step">1</span>
            {t('obligations.whatSection')}
          </h2>
          <Form.Item
            label={t('obligations.contract')}
            name="contract_id"
            rules={[{ required: true, message: t('validation.required') }]}
          >
            <ContractSelect
              ariaLabel={t('obligations.contract')}
              disabled={!isNew}
              known={existing.data?.contract ?? (contract.data ? contract.data : undefined)}
              onChange={(value) =>
                form.setFieldsValue({ contract_id: value, responsible_party_id: undefined })
              }
            />
          </Form.Item>
          <Form.Item
            label={t('obligations.titleField')}
            name="title"
            rules={[{ required: true, whitespace: true, message: t('validation.required') }]}
          >
            <Input maxLength={300} />
          </Form.Item>
          <Form.Item
            label={t('obligations.description')}
            name="description"
            rules={[{ required: true, whitespace: true, message: t('validation.required') }]}
          >
            <Input.TextArea rows={3} maxLength={5000} />
          </Form.Item>
          <Form.Item label={t('obligations.priority')} name="priority">
            <Segmented<Priority>
              options={PRIORITIES.map((value) => ({ value, label: t(`obligations.priorities.${value}`) }))}
            />
          </Form.Item>
          {isNew && (
            <Form.Item label={t('obligations.initialStatus')} name="status">
              <Segmented<ObligationStatus>
                options={(['pending', 'in_progress'] as const).map((value) => ({
                  value,
                  label: t(`obligations.statuses.${value}`),
                }))}
              />
            </Form.Item>
          )}
        </section>

        <section className="panel form-section">
          <h2 className="form-section-title">
            <span className="step">2</span>
            {t('obligations.whoSection')}
          </h2>
          <div className="form-grid">
            <Form.Item
              label={t('obligations.party')}
              name="responsible_party_id"
              extra={t('obligations.partyHelp')}
              rules={[{ required: true, message: t('validation.required') }]}
            >
              <Select options={partyOptions} disabled={!contractId} loading={contract.isFetching} />
            </Form.Item>
            <Form.Item
              label={t('obligations.owner')}
              name="responsible_user_id"
              extra={t('obligations.ownerHelp')}
            >
              <UserSelect ariaLabel={t('obligations.owner')} known={existing.data?.responsible_user} />
            </Form.Item>
          </div>
        </section>

        <section className="panel form-section">
          <h2 className="form-section-title">
            <span className="step">3</span>
            {t('obligations.whenSection')}
          </h2>
          <div className="form-grid">
            <Form.Item label={t('obligations.startDate')} name="start_date">
              <DatePicker className="full-width" />
            </Form.Item>
            <Form.Item
              label={t('obligations.due')}
              name="due_date"
              dependencies={['start_date', 'ongoing']}
              rules={[
                ({ getFieldValue }) => ({
                  validator: (_, due: Dayjs | null) => {
                    if (getFieldValue('ongoing')) return Promise.resolve()
                    if (!due) return Promise.reject(new Error(t('obligations.dueRequired')))
                    const start: Dayjs | null = getFieldValue('start_date')
                    return start && due.isBefore(start, 'day')
                      ? Promise.reject(new Error(t('obligations.dueBeforeStart')))
                      : Promise.resolve()
                  },
                }),
              ]}
            >
              <DatePicker className="full-width" disabled={ongoing} />
            </Form.Item>
          </div>
          <Form.Item name="ongoing" valuePropName="checked">
            <Checkbox>{t('obligations.ongoing')}</Checkbox>
          </Form.Item>
          {!ongoing && (
            <div className="form-grid">
              <Form.Item label={t('obligations.repeats')} name="repeat">
                <Select
                  options={[
                    { value: 'none', label: t('obligations.oneTime') },
                    ...(Object.keys(REPEAT_PRESETS) as RepeatPreset[]).map((value) => ({
                      value,
                      label: t(`obligations.repeat.${value}`),
                    })),
                    { value: 'custom', label: t('obligations.repeat.custom') },
                  ]}
                />
              </Form.Item>
              {repeat === 'custom' && (
                <Form.Item
                  label={t('obligations.customRule')}
                  name="custom_rule"
                  extra={t('obligations.customRuleHelp')}
                  rules={[{ required: true, whitespace: true, message: t('validation.required') }]}
                >
                  <Input maxLength={500} dir="ltr" placeholder="FREQ=MONTHLY;INTERVAL=2" />
                </Form.Item>
              )}
            </div>
          )}
        </section>

        <section className="panel form-section">
          <h2 className="form-section-title">
            <span className="step">4</span>
            {t('obligations.moreSection')}
          </h2>
          <Form.Item
            label={t('obligations.penalty')}
            name="penalty_text"
            extra={t('obligations.penaltyHelp')}
          >
            <Input.TextArea rows={2} maxLength={5000} />
          </Form.Item>
          <Form.Item label={t('obligations.notes')} name="notes">
            <Input.TextArea rows={2} maxLength={5000} />
          </Form.Item>
        </section>

        <div className="panel form-actions">
          <Button onClick={() => navigate(id ? `/obligations/${id}` : '/obligations')}>
            {t('common.cancel')}
          </Button>
          <Button type="primary" htmlType="submit" loading={saving}>
            {isNew ? t('obligations.create') : t('common.save')}
          </Button>
        </div>
      </Form>
    </div>
  )
}
