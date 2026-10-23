import { CheckCircleFilled, ExclamationCircleFilled } from '@ant-design/icons'
import { App, Button, DatePicker, Form, Input, InputNumber, Select, Spin } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useNavigate, useParams } from 'react-router-dom'
import { PageHeader } from '../../components/PageHeader'
import { showServerErrors } from '../../components/showServerErrors'
import {
  useContract,
  useContractDefaults,
  useContractStatuses,
  useContractTypes,
  useCreateContract,
  useUpdateContract,
  type StatusCode,
} from './api'
import { PartiesField, type PartyRow } from './PartiesField'
import { PropertySelect } from './pickers'
import { useContractFormat } from './useContractFormat'

const DAY = 'YYYY-MM-DD'

interface ContractFormValues {
  contract_number: string
  type_code: string
  title: string
  status_code: StatusCode
  property_ids: string[]
  description?: string
  start_date?: Dayjs
  end_date?: Dayjs | null
  value_amount?: number | null
  currency?: string
  renewal_date?: Dayjs | null
  parties: PartyRow[]
}

const SECTIONS = {
  basic: ['contract_number', 'type_code', 'title', 'status_code', 'property_ids', 'description'],
  dates: ['start_date', 'end_date', 'value_amount', 'currency', 'renewal_date'],
  parties: ['parties'],
} as const satisfies Record<string, (keyof ContractFormValues)[]>

const day = (value: Dayjs | null | undefined) => (value ? value.format(DAY) : null)

/** New contract (`/contracts/new`) and edit (`/contracts/:id/edit`): design screen 5 (FR-CON-01, FR-CON-04). */
export function ContractFormPage() {
  const { id } = useParams()
  const isNew = !id
  const { t } = useTranslation()
  const { message } = App.useApp()
  const navigate = useNavigate()
  const format = useContractFormat()
  const [form] = Form.useForm<ContractFormValues>()
  const [, setErrorsVersion] = useState(0)
  const existing = useContract(id)
  const defaults = useContractDefaults(isNew)
  const types = useContractTypes()
  const statuses = useContractStatuses()
  const create = useCreateContract()
  const update = useUpdateContract(id ?? '')
  const values = Form.useWatch([], form) as Partial<ContractFormValues> | undefined

  useEffect(() => {
    if (isNew && defaults.data) {
      form.setFieldsValue({
        contract_number: defaults.data.next_number,
        currency: defaults.data.default_currency,
      })
    }
  }, [isNew, defaults.data, form])

  useEffect(() => {
    const contract = existing.data
    if (!contract) return
    form.setFieldsValue({
      contract_number: contract.contract_number,
      type_code: contract.contract_type.code,
      title: contract.title,
      status_code: contract.status.code as StatusCode,
      property_ids: contract.properties.map((p) => p.id),
      description: contract.description ?? undefined,
      start_date: dayjs(contract.start_date),
      end_date: contract.end_date ? dayjs(contract.end_date) : null,
      value_amount: contract.value_amount === null ? null : Number(contract.value_amount),
      currency: contract.currency ?? undefined,
      renewal_date: contract.renewal_date ? dayjs(contract.renewal_date) : null,
      parties: contract.parties.map(({ id: partyId, display_name, party_type, role }) => ({
        id: partyId,
        display_name,
        party_type,
        role,
      })),
    })
  }, [existing.data, form])

  const submit = async (asDraft: boolean) => {
    let fields: ContractFormValues
    try {
      fields = await form.validateFields()
    } catch {
      setErrorsVersion((v) => v + 1)
      return
    }
    const hasValue = fields.value_amount !== null && fields.value_amount !== undefined
    const body = {
      contract_number: fields.contract_number,
      title: fields.title,
      type_code: fields.type_code,
      status_code: asDraft ? 'draft' : fields.status_code,
      start_date: day(fields.start_date)!,
      end_date: day(fields.end_date),
      value_amount: hasValue ? String(fields.value_amount) : null,
      currency: hasValue ? fields.currency || null : null,
      renewal_date: day(fields.renewal_date),
      description: fields.description || null,
      parties: fields.parties.map((row) => ({ party_id: row.id, role: row.role })),
      property_ids: fields.property_ids ?? [],
    } as const
    try {
      const saved = isNew ? await create.mutateAsync(body) : await update.mutateAsync(body)
      message.success(isNew ? t('contracts.created') : t('contracts.saved'))
      navigate(`/contracts/${saved.id}`)
    } catch (err) {
      showServerErrors(err, form, message, t)
      setErrorsVersion((v) => v + 1)
    }
  }

  if (!isNew && existing.isLoading) return <Spin />
  // Archived contracts are read-only; the details page explains how to restore them.
  if (existing.data?.archived_at) return <Navigate to={`/contracts/${existing.data.id}`} replace />

  const saving = create.isPending || update.isPending
  const errorsIn = (names: readonly string[]) =>
    form.getFieldsError(names as never).reduce((count, field) => count + (field.errors.length ? 1 : 0), 0)
  const totalErrors = errorsIn(Object.values(SECTIONS).flat())
  const filled = (names: (keyof ContractFormValues)[]) =>
    names.every((name) => {
      const value = values?.[name]
      return Array.isArray(value) ? value.length > 0 : value !== undefined && value !== null && value !== ''
    })
  const progress = [
    { key: 'basic', done: filled(['contract_number', 'type_code', 'title', 'status_code']) },
    { key: 'dates', done: filled(['start_date']) },
    { key: 'parties', done: filled(['parties']), count: values?.parties?.length ?? 0 },
  ] as const

  // A new contract starts as draft or active; an existing one may move only along its allowed transitions (D-17).
  const currentStatus = existing.data?.status
  const statusCodes: string[] = currentStatus
    ? [currentStatus.code, ...currentStatus.next_codes]
    : ['draft', 'active']
  const statusOptions = (statuses.data ?? [])
    .filter((status) => statusCodes.includes(status.code))
    .map((status) => ({ value: status.code, label: format.name(status) }))
  const title = isNew ? t('contracts.new') : t('contracts.edit')

  return (
    <div className="page">
      <PageHeader
        title={title}
        subtitle={t('contracts.formSubtitle')}
        breadcrumb={[
          { label: t('contracts.title'), to: '/contracts' },
          ...(existing.data
            ? [{ label: existing.data.contract_number, to: `/contracts/${existing.data.id}` }]
            : []),
          { label: title },
        ]}
      />
      <div className="form-with-aside">
        <Form<ContractFormValues>
          form={form}
          layout="vertical"
          initialValues={{ status_code: 'draft', property_ids: [], parties: [] }}
          onFieldsChange={() => setErrorsVersion((v) => v + 1)}
          disabled={saving}
          requiredMark
        >
          <section className="panel form-section">
            <h2 className="form-section-title">
              <span className="step">1</span>
              {t('contracts.basicSection')}
            </h2>
            <div className="form-grid">
              <Form.Item
                label={t('contracts.number')}
                name="contract_number"
                extra={isNew ? t('contracts.numberHelp') : undefined}
                normalize={(value: string) => value.toUpperCase()}
                rules={[
                  { required: true, whitespace: true, message: t('validation.required') },
                  { pattern: /^[A-Z0-9][A-Z0-9 ._/-]*$/, message: t('contracts.numberFormat') },
                ]}
              >
                <Input maxLength={100} dir="ltr" />
              </Form.Item>
              <Form.Item
                label={t('contracts.type')}
                name="type_code"
                rules={[{ required: true, message: t('validation.required') }]}
              >
                <Select
                  loading={types.isLoading}
                  options={(types.data ?? []).map((type) => ({ value: type.code, label: format.name(type) }))}
                />
              </Form.Item>
            </div>
            <Form.Item
              label={t('contracts.titleField')}
              name="title"
              rules={[{ required: true, whitespace: true, message: t('validation.required') }]}
            >
              <Input maxLength={300} />
            </Form.Item>
            <div className="form-grid">
              <Form.Item label={t('contracts.status')} name="status_code" rules={[{ required: true }]}>
                <Select options={statusOptions} loading={statuses.isLoading} />
              </Form.Item>
              <Form.Item label={t('contracts.properties')} name="property_ids">
                <PropertySelect
                  multiple
                  ariaLabel={t('contracts.properties')}
                  known={existing.data?.properties}
                />
              </Form.Item>
            </div>
            <Form.Item label={t('contracts.description')} name="description">
              <Input.TextArea rows={3} maxLength={5000} />
            </Form.Item>
          </section>

          <section className="panel form-section">
            <h2 className="form-section-title">
              <span className="step">2</span>
              {t('contracts.datesSection')}
            </h2>
            <div className="form-grid">
              <Form.Item
                label={t('contracts.startDate')}
                name="start_date"
                rules={[{ required: true, message: t('validation.required') }]}
              >
                <DatePicker className="full-width" />
              </Form.Item>
              <Form.Item
                label={t('contracts.endDate')}
                name="end_date"
                extra={t('contracts.endDateHelp')}
                dependencies={['start_date']}
                rules={[
                  ({ getFieldValue }) => ({
                    validator: (_, end: Dayjs | null) => {
                      const start: Dayjs | undefined = getFieldValue('start_date')
                      return end && start && end.isBefore(start, 'day')
                        ? Promise.reject(new Error(t('contracts.endBeforeStart')))
                        : Promise.resolve()
                    },
                  }),
                ]}
              >
                <DatePicker className="full-width" />
              </Form.Item>
            </div>
            <div className="form-grid">
              <Form.Item label={t('contracts.value')} extra={t('contracts.currencyHelp')}>
                <div className="value-input">
                  <Form.Item name="value_amount" noStyle>
                    <InputNumber<number>
                      min={0}
                      precision={2}
                      className="full-width"
                      aria-label={t('contracts.value')}
                      formatter={(v) =>
                        v === undefined || v === null ? '' : `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
                      }
                      parser={(v) => Number((v ?? '').replace(/,/g, ''))}
                    />
                  </Form.Item>
                  <Form.Item
                    name="currency"
                    noStyle
                    normalize={(v: string) => v.toUpperCase()}
                    rules={[{ pattern: /^[A-Z]{3}$/, message: t('contracts.currencyFormat') }]}
                  >
                    <Input
                      maxLength={3}
                      className="currency-input"
                      aria-label={t('contracts.currency')}
                      dir="ltr"
                    />
                  </Form.Item>
                </div>
              </Form.Item>
              <Form.Item
                label={t('contracts.renewalDate')}
                name="renewal_date"
                extra={t('contracts.renewalHelp')}
              >
                <DatePicker className="full-width" />
              </Form.Item>
            </div>
          </section>

          <section className="panel form-section">
            <h2 className="form-section-title">
              <span className="step">3</span>
              {t('contracts.partiesSection')} <span className="required-star">*</span>
            </h2>
            <Form.Item
              name="parties"
              rules={[{ type: 'array', min: 1, message: t('contracts.partiesRequired') }]}
            >
              <PartiesField />
            </Form.Item>
          </section>

          <div className="panel form-footer">
            <span className="form-footer-status">
              {totalErrors > 0 && (
                <span className="text-danger">
                  <ExclamationCircleFilled /> {t('contracts.fieldsToFix', { count: totalErrors })}
                </span>
              )}
            </span>
            <Button onClick={() => navigate(existing.data ? `/contracts/${existing.data.id}` : '/contracts')}>
              {t('common.cancel')}
            </Button>
            {isNew && (
              <Button onClick={() => submit(true)} loading={saving}>
                {t('contracts.saveDraft')}
              </Button>
            )}
            <Button type="primary" onClick={() => submit(false)} loading={saving}>
              {isNew ? t('contracts.create') : t('contracts.saveChanges')}
            </Button>
          </div>
        </Form>

        <aside className="panel form-aside">
          <h2 className="panel-title">{t('contracts.progress')}</h2>
          <ul className="progress-list">
            {progress.map((step) => {
              const issues = errorsIn(SECTIONS[step.key])
              return (
                <li key={step.key} className={issues ? 'is-error' : step.done ? 'is-done' : ''}>
                  {issues ? (
                    <ExclamationCircleFilled />
                  ) : step.done ? (
                    <CheckCircleFilled />
                  ) : (
                    <span className="progress-dot" />
                  )}
                  <span>
                    {t(`contracts.progressSteps.${step.key}`)}
                    {issues > 0 && ` — ${t('contracts.issues', { count: issues })}`}
                    {!issues &&
                      step.key === 'parties' &&
                      step.count > 0 &&
                      ` — ${t('contracts.partiesAdded', { count: step.count })}`}
                  </span>
                </li>
              )
            })}
          </ul>
        </aside>
      </div>
    </div>
  )
}
