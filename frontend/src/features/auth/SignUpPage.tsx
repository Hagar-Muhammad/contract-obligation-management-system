import { Alert, Button, Form, Input, Select, Typography } from 'antd'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { ApiError } from '../../api/errors'
import { useAuth, type SignUpData } from '../../auth/context'
import { useLanguage } from '../../i18n/useLanguage'
import { AuthLayout } from './AuthLayout'

const PASSWORD_MIN_LENGTH = 8

interface SignUpForm extends SignUpData {
  confirm: string
}

/** Self sign-up (CR-01). The server assigns the role; the visitor cannot choose it. */
export function SignUpPage() {
  const { t } = useTranslation()
  const { language } = useLanguage()
  const { status, register } = useAuth()
  const navigate = useNavigate()
  const [form] = Form.useForm<SignUpForm>()
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (status === 'authenticated') {
    return <Navigate to="/" replace />
  }

  const onFinish = async ({ confirm: _confirm, ...data }: SignUpForm) => {
    setError(null)
    setSubmitting(true)
    try {
      await register(data)
      navigate('/', { replace: true })
    } catch (err) {
      if (!(err instanceof ApiError)) throw err
      if (err.status === 409) {
        form.setFields([{ name: 'email', errors: [t('signup.emailTaken')] }])
      } else if (err.status === 403) {
        setError(t('signup.disabled'))
      } else if (Object.keys(err.fieldErrors()).length) {
        form.setFields(
          Object.entries(err.fieldErrors()).map(([name, message]) => ({
            name: name as keyof SignUpForm,
            errors: [message],
          })),
        )
      } else {
        setError(t('signup.failed'))
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout>
      <h2 className="auth-title">{t('signup.title')}</h2>
      <p className="auth-subtitle">{t('signup.subtitle')}</p>
      {error && <Alert type="error" title={error} showIcon className="auth-error" role="alert" />}
      <Form<SignUpForm>
        form={form}
        layout="vertical"
        size="large"
        onFinish={onFinish}
        requiredMark={false}
        disabled={submitting}
        initialValues={{ preferred_language: language }}
      >
        <Form.Item
          label={t('signup.name')}
          name="full_name"
          rules={[{ required: true, whitespace: true, message: t('validation.required') }]}
        >
          <Input autoComplete="name" maxLength={200} autoFocus />
        </Form.Item>
        <Form.Item
          label={t('signup.email')}
          name="email"
          rules={[
            { required: true, message: t('validation.required') },
            { type: 'email', message: t('validation.email') },
          ]}
        >
          <Input type="email" autoComplete="email" maxLength={320} />
        </Form.Item>
        <Form.Item
          label={t('signup.password')}
          name="password"
          rules={[
            { required: true, message: t('validation.required') },
            {
              min: PASSWORD_MIN_LENGTH,
              message: t('validation.passwordLength', { min: PASSWORD_MIN_LENGTH }),
            },
          ]}
        >
          <Input.Password
            autoComplete="new-password"
            maxLength={128}
            iconRender={(visible) => (
              <span className="password-toggle">{visible ? t('login.hide') : t('login.show')}</span>
            )}
          />
        </Form.Item>
        <Form.Item
          label={t('signup.confirm')}
          name="confirm"
          dependencies={['password']}
          rules={[
            { required: true, message: t('validation.required') },
            ({ getFieldValue }) => ({
              validator: (_, value: string) =>
                !value || value === getFieldValue('password')
                  ? Promise.resolve()
                  : Promise.reject(new Error(t('signup.mismatch'))),
            }),
          ]}
        >
          <Input.Password
            autoComplete="new-password"
            maxLength={128}
            iconRender={(visible) => (
              <span className="password-toggle">{visible ? t('login.hide') : t('login.show')}</span>
            )}
          />
        </Form.Item>
        <Form.Item label={t('signup.language')} name="preferred_language">
          <Select
            options={[
              { value: 'en', label: t('language.en') },
              { value: 'ar', label: t('language.ar') },
            ]}
          />
        </Form.Item>
        <Typography.Paragraph type="secondary" className="auth-note">
          {t('signup.roleNote')}
        </Typography.Paragraph>
        <Button type="primary" htmlType="submit" block loading={submitting} className="auth-submit">
          {t('signup.submit')}
        </Button>
      </Form>
      <p className="auth-switch">
        {t('signup.haveAccount')} <Link to="/login">{t('signup.signIn')}</Link>
      </p>
    </AuthLayout>
  )
}
