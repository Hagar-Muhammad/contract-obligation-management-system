import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { isRtl, persistLanguage, type Language } from '.'

/** Current language and layout direction; keeps <html lang/dir> in sync. */
export function useLanguage() {
  const { i18n } = useTranslation()
  const language = (i18n.resolvedLanguage ?? 'en') as Language
  const direction: 'rtl' | 'ltr' = isRtl(language) ? 'rtl' : 'ltr'

  useEffect(() => {
    document.documentElement.lang = language
    document.documentElement.dir = direction
  }, [language, direction])

  const setLanguage = (lng: Language) => {
    persistLanguage(lng)
    void i18n.changeLanguage(lng)
  }

  return { language, direction, setLanguage }
}
