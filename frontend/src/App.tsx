import { ConfigProvider, Layout, Segmented, Space, Typography } from 'antd'
import arEG from 'antd/locale/ar_EG'
import enUS from 'antd/locale/en_US'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { isRtl, persistLanguage, SUPPORTED_LANGUAGES, type Language } from './i18n'

const ANTD_LOCALES = { en: enUS, ar: arEG } as const

function App() {
  const { t, i18n } = useTranslation()
  const language = (i18n.resolvedLanguage ?? 'en') as Language
  const direction = isRtl(language) ? 'rtl' : 'ltr'

  useEffect(() => {
    document.documentElement.lang = language
    document.documentElement.dir = direction
  }, [language, direction])

  const changeLanguage = (lng: Language) => {
    persistLanguage(lng)
    void i18n.changeLanguage(lng)
  }

  return (
    <ConfigProvider direction={direction} locale={ANTD_LOCALES[language]}>
      <Layout className="app-layout">
        <Layout.Header className="app-header">
          <Typography.Title level={4} className="app-title">
            {t('app.title')}
          </Typography.Title>
          <Segmented<Language>
            aria-label={t('language.label')}
            value={language}
            onChange={changeLanguage}
            options={SUPPORTED_LANGUAGES.map((lng) => ({ value: lng, label: t(`language.${lng}`) }))}
          />
        </Layout.Header>
        <Layout.Content className="app-content">
          <Space direction="vertical">
            <Typography.Title level={2}>{t('app.welcome')}</Typography.Title>
            <Typography.Paragraph>{t('app.placeholder')}</Typography.Paragraph>
          </Space>
        </Layout.Content>
      </Layout>
    </ConfigProvider>
  )
}

export default App
