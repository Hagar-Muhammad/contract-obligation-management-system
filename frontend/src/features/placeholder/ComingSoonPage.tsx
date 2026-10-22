import { Button, Result } from 'antd'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

/** Shown for sidebar pages that a later module builds, so the navigation matches the design today. */
export function ComingSoonPage({ labelKey, module }: { labelKey: string; module: number }) {
  const { t } = useTranslation()
  return (
    <Result
      className="panel coming-soon"
      status="info"
      title={t('comingSoon.title', { page: t(labelKey) })}
      subTitle={module > 0 ? t('comingSoon.module', { module }) : t('comingSoon.later')}
      extra={
        <Link to="/">
          <Button type="primary">{t('comingSoon.back')}</Button>
        </Link>
      }
    />
  )
}
