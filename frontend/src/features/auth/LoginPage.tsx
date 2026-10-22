import { Alert, Button, Form, Input, Typography } from 'antd'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../../api/errors'
import { useAuth } from '../../auth/context'
import { AuthLayout } from './AuthLayout'
import { useAuthOptions } from './useAuthOptions'

interface LoginForm {
  email: string
  password: string
}

export function LoginPage() {
  const { t } = useTranslation()
  const { status, login } = useAuth()
  const options = useAuthOptions()
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const returnTo = (location.state as { from?: string } | null)?.from ?? '/'

  if (status === 'authenticated') {
    return <Navigate to={returnTo} replace />
  }

  const onFinish = async ({ email, password }: LoginForm) => {
    setError(null)
    setSubmitting(true)
    try {
      await login(email, password)
      navigate(returnTo, { replace: true })
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401 ? t('login.invalid') : t('login.failed'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout>
      <Typography.Title level={2} className="auth-title">
        {t('login.title')}
      </Typography.Title>
      <Typography.Paragraph type="secondary">{t('login.subtitle')}</Typography.Paragraph>
      {error && <Alert type="error" title={error} showIcon className="auth-error" role="alert" />}
      <Form<LoginForm>
        layout="vertical"
        size="large"
        onFinish={onFinish}
        requiredMark={false}
        disabled={submitting}
      >
        <Form.Item
          label={t('login.email')}
          name="email"
          rules={[{ required: true, message: t('validation.required') }]}
        >
          <Input type="email" autoComplete="username" autoFocus />
        </Form.Item>
        <Form.Item
          label={t('login.password')}
          name="password"
          rules={[{ required: true, message: t('validation.required') }]}
        >
          <Input.Password autoComplete="current-password" />
        </Form.Item>
        <Button type="primary" htmlType="submit" block loading={submitting}>
          {t('login.submit')}
        </Button>
      </Form>
      {options.data?.self_signup_enabled && (
        <Typography.Paragraph className="auth-switch">
          {t('login.noAccount')} <Link to="/signup">{t('login.createAccount')}</Link>
        </Typography.Paragraph>
      )}
    </AuthLayout>
  )
}
