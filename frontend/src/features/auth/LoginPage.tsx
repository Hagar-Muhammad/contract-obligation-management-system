import { Alert, Button, Card, Form, Input, Typography } from 'antd'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../../api/errors'
import { useAuth } from '../../auth/context'
import { LanguageSwitch } from '../../components/LanguageSwitch'
import { Logo } from '../../components/Logo'

interface LoginForm {
  email: string
  password: string
}

export function LoginPage() {
  const { t } = useTranslation()
  const { status, login } = useAuth()
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
    <div className="login-page">
      <div className="login-language">
        <LanguageSwitch />
      </div>
      <Card className="login-card">
        <div className="login-brand">
          <Logo size={44} />
          <Typography.Text type="secondary">{t('app.tagline')}</Typography.Text>
        </div>
        <Typography.Title level={4}>{t('login.title')}</Typography.Title>
        {error && <Alert type="error" message={error} showIcon className="login-error" role="alert" />}
        <Form<LoginForm> layout="vertical" onFinish={onFinish} requiredMark={false} disabled={submitting}>
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
      </Card>
    </div>
  )
}
