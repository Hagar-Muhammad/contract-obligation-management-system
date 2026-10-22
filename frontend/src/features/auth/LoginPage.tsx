import { InfoCircleOutlined } from '@ant-design/icons'
import { Alert, App, Button, Checkbox, Form, Input } from 'antd'
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
  remember: boolean
}

export function LoginPage() {
  const { t } = useTranslation()
  const { modal } = App.useApp()
  const { status, login } = useAuth()
  const options = useAuthOptions()
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const returnTo = (location.state as { from?: string } | null)?.from ?? '/'
  const signupEnabled = options.data?.self_signup_enabled ?? false

  if (status === 'authenticated') {
    return <Navigate to={returnTo} replace />
  }

  const onFinish = async ({ email, password, remember }: LoginForm) => {
    setError(null)
    setSubmitting(true)
    try {
      await login(email, password, remember)
      navigate(returnTo, { replace: true })
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401 ? t('login.invalid') : t('login.failed'))
    } finally {
      setSubmitting(false)
    }
  }

  const showForgotPassword = () =>
    modal.info({ title: t('login.forgotTitle'), content: t('login.forgotText'), okText: 'OK' })

  return (
    <AuthLayout>
      <h2 className="auth-title">{t('login.title')}</h2>
      <p className="auth-subtitle">{signupEnabled ? t('login.subtitle') : t('login.subtitleAdminOnly')}</p>
      {error && <Alert type="error" title={error} showIcon className="auth-error" role="alert" />}
      <Form<LoginForm>
        layout="vertical"
        size="large"
        onFinish={onFinish}
        requiredMark={false}
        disabled={submitting}
        initialValues={{ remember: false }}
      >
        <Form.Item
          label={t('login.email')}
          name="email"
          rules={[{ required: true, message: t('validation.required') }]}
        >
          <Input type="email" autoComplete="username" placeholder={t('login.emailPlaceholder')} autoFocus />
        </Form.Item>
        <div className="auth-label-row">
          <label htmlFor="password">{t('login.password')}</label>
          <button type="button" className="link-button" onClick={showForgotPassword}>
            {t('login.forgot')}
          </button>
        </div>
        <Form.Item name="password" rules={[{ required: true, message: t('validation.required') }]}>
          <Input.Password
            id="password"
            autoComplete="current-password"
            aria-label={t('login.password')}
            iconRender={(visible) => (
              <span className="password-toggle">{visible ? t('login.hide') : t('login.show')}</span>
            )}
          />
        </Form.Item>
        <Form.Item name="remember" valuePropName="checked" className="auth-remember">
          <Checkbox>{t('login.remember')}</Checkbox>
        </Form.Item>
        <Button type="primary" htmlType="submit" block loading={submitting} className="auth-submit">
          {t('login.submit')}
        </Button>
      </Form>
      <div className="auth-info" role="note">
        <InfoCircleOutlined className="auth-info-icon" />
        {signupEnabled ? (
          <span>
            {t('login.noAccount')} <Link to="/signup">{t('login.createAccount')}</Link>
          </span>
        ) : (
          <span>{t('login.adminOnly')}</span>
        )}
      </div>
    </AuthLayout>
  )
}
