import { Segmented } from 'antd'
import { useTranslation } from 'react-i18next'
import { SUPPORTED_LANGUAGES, type Language } from '../i18n'
import { useLanguage } from '../i18n/useLanguage'

export function LanguageSwitch() {
  const { t } = useTranslation()
  const { language, setLanguage } = useLanguage()
  return (
    <Segmented<Language>
      aria-label={t('language.label')}
      value={language}
      onChange={setLanguage}
      options={SUPPORTED_LANGUAGES.map((lng) => ({ value: lng, label: t(`language.${lng}`) }))}
    />
  )
}
