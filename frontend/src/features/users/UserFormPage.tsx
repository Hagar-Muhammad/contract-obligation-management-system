import { App, Button, Form, Input, Popconfirm, Select, Spin } from 'antd'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../../api/errors'
import { useAuth } from '../../auth/context'
import { ROLE_CODES } from '../../auth/roles'
import { PageHeader } from '../../components/PageHeader'
import { useCreateUser, useRoles, useSetUserActive, useUpdateUser, useUser, type RoleCode } from './api'

const PASSWORD_MIN_LENGTH = 8

interface UserFormValues {
  full_name: string
  email: string
  password?: string
  role_codes: RoleCode[]
  preferred_language: 'en' | 'ar'
}

/** Create (`/users/new`) and edit (`/users/:id`) a user (FR-USER-01..03). */
export function UserFormPage() {
  const { id } = useParams()
  const isNew = !id
  const { t } = useTranslation()
  const { message } = App.useApp()
  const { user: me } = useAuth()
  const navigate = useNavigate()
  const [form] = Form.useForm<UserFormValues>()
  const roles = useRoles()
  const existing = useUser(id)
  const create = useCreateUser()
  const update = useUpdateUser(id ?? '')
  const setActive = useSetUserActive()

  useEffect(() => {
    if (existing.data) {
      form.setFieldsValue({
        full_name: existing.data.full_name,
        email: existing.data.email,
        role_codes: existing.data.role_codes as RoleCode[],
        preferred_language: existing.data.preferred_language as 'en' | 'ar',
      })
    }
  }, [existing.data, form])

  const onFinish = async (values: UserFormValues) => {
    try {
      if (isNew) {
        await create.mutateAsync({ ...values, password: values.password ?? '' })
        message.success(t('users.created'))
      } else {
        await update.mutateAsync({ ...values, password: values.password || undefined })
        message.success(t('users.saved'))
      }
      navigate('/users')
    } catch (err) {
      if (!(err instanceof ApiError)) throw err
      const fields = err.fieldErrors()
      if (err.status === 409) fields.email = t('users.emailTaken')
      const entries = Object.entries(fields)
      if (entries.length) {
        form.setFields(
          entries.map(([name, error]) => ({ name: name as keyof UserFormValues, errors: [error] })),
        )
      } else {
        message.error(err.message || t('errors.generic'))
      }
    }
  }

  const toggleActive = async (active: boolean) => {
    if (!id) return
    await setActive.mutateAsync({ id, active })
    message.success(t(active ? 'users.activated' : 'users.deactivated'))
    navigate('/users')
  }

  if (!isNew && existing.isLoading) return <Spin />

  const title = isNew ? t('users.new') : t('users.edit')
  const roleOptions = ROLE_CODES.filter((code) => roles.data?.some((r) => r.code === code)).map((code) => ({
    value: code as RoleCode,
    label: t(`roles.${code}`),
  }))
  const saving = create.isPending || update.isPending

  return (
    <div className="page page-narrow">
      <PageHeader
        title={existing.data?.full_name ?? title}
        breadcrumb={[{ label: t('users.title'), to: '/users' }, { label: title }]}
      />
      <Form<UserFormValues>
        form={form}
        layout="vertical"
        onFinish={onFinish}
        initialValues={{ preferred_language: 'en', role_codes: [] }}
        disabled={saving}
      >
        <section className="panel form-section">
          <h2 className="form-section-title">
            <span className="step">1</span>
            {t('users.detailsSection')}
          </h2>
          <div className="form-grid">
            <Form.Item
              label={t('users.name')}
              name="full_name"
              rules={[{ required: true, whitespace: true, message: t('validation.required') }]}
            >
              <Input maxLength={200} />
            </Form.Item>
            <Form.Item
              label={t('users.email')}
              name="email"
              rules={[
                { required: true, message: t('validation.required') },
                { type: 'email', message: t('validation.email') },
              ]}
            >
              <Input type="email" maxLength={320} />
            </Form.Item>
          </div>
          <Form.Item label={t('users.language')} name="preferred_language" className="form-narrow">
            <Select
              options={[
                { value: 'en', label: t('language.en') },
                { value: 'ar', label: t('language.ar') },
              ]}
            />
          </Form.Item>
        </section>

        <section className="panel form-section">
          <h2 className="form-section-title">
            <span className="step">2</span>
            {t('users.accessSection')}
          </h2>
          <Form.Item
            label={t('users.roles')}
            name="role_codes"
            rules={[{ required: true, type: 'array', min: 1, message: t('users.rolesRequired') }]}
          >
            <Select<RoleCode[]> mode="multiple" loading={roles.isLoading} options={roleOptions} />
          </Form.Item>
          <Form.Item
            label={isNew ? t('users.password') : t('users.newPassword')}
            name="password"
            extra={isNew ? undefined : t('users.newPasswordHelp')}
            rules={[
              { required: isNew, message: t('validation.required') },
              {
                min: PASSWORD_MIN_LENGTH,
                message: t('validation.passwordLength', { min: PASSWORD_MIN_LENGTH }),
              },
            ]}
          >
            <Input.Password autoComplete="new-password" maxLength={128} />
          </Form.Item>
        </section>

        <div className="panel form-actions">
          <Button onClick={() => navigate('/users')}>{t('users.cancel')}</Button>
          <Button type="primary" htmlType="submit" loading={saving}>
            {t('users.save')}
          </Button>
        </div>
      </Form>

      {!isNew && existing.data && existing.data.id !== me?.id && (
        <section className="panel form-section danger-zone">
          <h2 className="form-section-title">{t('users.accessTitle')}</h2>
          {existing.data.is_active ? (
            <>
              <p className="panel-subtitle">{t('users.deactivateHelp')}</p>
              <Popconfirm title={t('users.deactivateConfirm')} onConfirm={() => toggleActive(false)}>
                <Button danger loading={setActive.isPending}>
                  {t('users.deactivate')}
                </Button>
              </Popconfirm>
            </>
          ) : (
            <>
              <p className="panel-subtitle">{t('users.reactivateHelp')}</p>
              <Button onClick={() => toggleActive(true)} loading={setActive.isPending}>
                {t('users.reactivate')}
              </Button>
            </>
          )}
        </section>
      )}
    </div>
  )
}
