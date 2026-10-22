import { Card, Space, Tag, Typography } from 'antd'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../auth/context'

export function HomePage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  return (
    <Space orientation="vertical" size="large" className="page">
      <Typography.Title level={2}>{t('home.welcome', { name: user?.full_name })}</Typography.Title>
      <Card title={t('home.yourRoles')}>
        <Space wrap>
          {user?.roles.map((role) => (
            <Tag key={role}>{t(`roles.${role}`)}</Tag>
          ))}
        </Space>
      </Card>
      <Typography.Paragraph type="secondary">{t('home.placeholder')}</Typography.Paragraph>
    </Space>
  )
}
