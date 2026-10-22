import { BellOutlined, SafetyCertificateOutlined, ScanOutlined } from '@ant-design/icons'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { LanguageSwitch } from '../../components/LanguageSwitch'
import { Logo } from '../../components/Logo'

const FEATURES = [
  { key: 'extract', icon: <ScanOutlined />, tone: 'blue' },
  { key: 'remind', icon: <BellOutlined />, tone: 'green' },
  { key: 'audit', icon: <SafetyCertificateOutlined />, tone: 'amber' },
] as const
const YEAR = new Date().getFullYear()

/** Full-screen sign-in / sign-up layout (docs/design/ConTrack-UI.pdf, screen 1). */
export function AuthLayout({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  return (
    <div className="auth-page">
      <aside className="auth-hero">
        <Logo variant="dark" size={36} />
        <div className="auth-hero-body">
          <p className="auth-eyebrow">{t('auth.eyebrow')}</p>
          <h1 className="auth-hero-title">
            <span>{t('auth.heroLine1')}</span>
            <span>{t('auth.heroLine2')}</span>
            <span>{t('auth.heroLine3')}</span>
          </h1>
          <p className="auth-hero-text">{t('auth.heroText')}</p>
          <ul className="auth-features">
            {FEATURES.map(({ key, icon, tone }) => (
              <li key={key}>
                <span className={`auth-feature-icon tone-${tone}`}>{icon}</span>
                <span>{t(`auth.features.${key}`)}</span>
              </li>
            ))}
          </ul>
          <div className="auth-samples" aria-hidden="true">
            <div className="auth-sample">
              <span className="auth-sample-dot tone-blue" />
              <span className="auth-sample-text">
                <strong>{t('auth.sample.rentTitle')}</strong>
                <small>{t('auth.sample.rentMeta')}</small>
              </span>
              <span className="auth-sample-badge tone-blue">{t('auth.sample.rentDue')}</span>
            </div>
            <div className="auth-sample auth-sample-offset">
              <span className="auth-sample-dot tone-green" />
              <span className="auth-sample-text">
                <strong>{t('auth.sample.fitoutTitle')}</strong>
                <small>{t('auth.sample.fitoutMeta')}</small>
              </span>
              <span className="auth-sample-badge tone-green">{t('auth.sample.fitoutDone')}</span>
            </div>
          </div>
        </div>
        <small className="auth-hero-footer">{t('auth.rights', { year: YEAR })}</small>
      </aside>
      <main className="auth-main">
        <div className="auth-toolbar">
          <LanguageSwitch />
        </div>
        <div className="auth-form">{children}</div>
      </main>
    </div>
  )
}
