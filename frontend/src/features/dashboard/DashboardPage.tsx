import { Space, Tag } from 'antd'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../auth/context'
import { ROLE_TAG_CLASS, type RoleCodeName } from '../../auth/roles'
import { PageHeader } from '../../components/PageHeader'
import { useLanguage } from '../../i18n/useLanguage'

function greetingKey(hour: number): string {
  if (hour < 12) return 'dashboard.morning'
  if (hour < 18) return 'dashboard.afternoon'
  return 'dashboard.evening'
}

/** Dashboard greeting from the design; KPIs and deadlines arrive with module 10 (FR-REP-*). */
export function DashboardPage() {
  const { t } = useTranslation()
  const { language } = useLanguage()
  const { user } = useAuth()
  const [now] = useState(() => new Date())
  const firstName = user?.full_name.split(/\s+/)[0] ?? ''
  const date = new Intl.DateTimeFormat(language === 'ar' ? 'ar-EG-u-nu-latn' : 'en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(now)

  return (
    <div className="page">
      <PageHeader
        title={t(greetingKey(now.getHours()), { name: firstName })}
        subtitle={t('dashboard.subtitle', { date })}
      />
      <section className="panel">
        <h2 className="panel-title">{t('dashboard.emptyTitle')}</h2>
        <p className="panel-subtitle panel-gap">{t('dashboard.emptyText')}</p>
        <Space wrap>
          {user?.roles.map((role) => (
            <Tag key={role} className={ROLE_TAG_CLASS[role as RoleCodeName]}>
              {t(`roles.${role}`)}
            </Tag>
          ))}
        </Space>
      </section>
    </div>
  )
}
