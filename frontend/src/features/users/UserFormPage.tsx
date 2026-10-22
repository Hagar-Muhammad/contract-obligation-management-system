import { App, Button, Card, Form, Input, Select, Space, Spin, Typography } from 'antd'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../../api/errors'
import { useCreateUser, useRoles, useUpdateUser, useUser, type RoleCode } from './api'

const PASSWORD_MIN_LENGTH = 8

interface UserFormValues {
  full_name: string
  email: string
  password?: string
  role_codes: RoleCode[]
  preferred_language: 'en' | 'ar'
}

/** Create (`/users/new`) and edit (`/users/:id`) a user (FR-USER-01, FR-USER-02). */
export function UserFormPage() {
  const { id } = useParams()
  const isNew = !id
  const { t } = useTranslation()
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [form] = Form.useForm<UserFormValues>()
  const roles = useRoles()
  const existing = useUser(id)
  const create = useCreateUser()
  const update = useUpdateUser(id ?? '')

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

  if (!isNew && existing.isLoading) return <Spin />

  return (
    <Space orientation="vertical" size="middle" className="page">
      <Typography.Title level={2}>{isNew ? t('users.new') : t('users.edit')}</Typography.Title>
      <Card className="form-card">
        <Form<UserFormValues>
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{ preferred_language: 'en', role_codes: [] }}
          disabled={create.isPending || update.isPending}
        >
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
          <Form.Item
            label={t('users.roles')}
            name="role_codes"
            rules={[{ required: true, type: 'array', min: 1, message: t('users.rolesRequired') }]}
          >
            <Select<RoleCode[]>
              mode="multiple"
              loading={roles.isLoading}
              options={roles.data?.map((role) => ({
                value: role.code as RoleCode,
                label: t(`roles.${role.code}`),
              }))}
            />
          </Form.Item>
          <Form.Item label={t('users.language')} name="preferred_language">
            <Select
              options={[
                { value: 'en', label: t('language.en') },
                { value: 'ar', label: t('language.ar') },
              ]}
            />
          </Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={create.isPending || update.isPending}>
              {t('users.save')}
            </Button>
            <Button onClick={() => navigate('/users')}>{t('users.cancel')}</Button>
          </Space>
        </Form>
      </Card>
    </Space>
  )
}
