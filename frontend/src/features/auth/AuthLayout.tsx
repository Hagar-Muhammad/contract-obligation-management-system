import { CheckCircleFilled } from '@ant-design/icons'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { LanguageSwitch } from '../../components/LanguageSwitch'
import { Logo, LogoMark } from '../../components/Logo'

const FEATURES = ['track', 'extract', 'remind', 'bilingual'] as const
const YEAR = new Date().getFullYear()

/** Full-screen layout for sign-in and sign-up: brand panel on one side, the form on the other. */
export function AuthLayout({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  return (
    <div className="auth-page">
      <aside className="auth-hero">
        <Logo variant="dark" size={40} />
        <div className="auth-hero-body">
          <h1 className="auth-hero-title">{t('auth.heroTitle')}</h1>
          <p className="auth-hero-text">{t('auth.heroText')}</p>
          <ul className="auth-features">
            {FEATURES.map((key) => (
              <li key={key}>
                <CheckCircleFilled className="auth-feature-icon" />
                {t(`auth.features.${key}`)}
              </li>
            ))}
          </ul>
        </div>
        <small className="auth-hero-footer">{t('auth.rights', { year: YEAR })}</small>
        <div className="auth-hero-watermark" aria-hidden="true">
          <LogoMark variant="dark" size={420} />
        </div>
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
