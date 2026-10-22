import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import ar from './locales/ar.json'
import en from './locales/en.json'

export const SUPPORTED_LANGUAGES = ['en', 'ar'] as const
export type Language = (typeof SUPPORTED_LANGUAGES)[number]

const RTL_LANGUAGES: ReadonlySet<string> = new Set(['ar'])
const STORAGE_KEY = 'coms.language'

export const isRtl = (lng: string): boolean => RTL_LANGUAGES.has(lng)

function readStoredLanguage(): Language {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored && (SUPPORTED_LANGUAGES as readonly string[]).includes(stored)) {
      return stored as Language
    }
  } catch {
    // Storage can be unavailable (private mode, blocked site data).
  }
  return 'en'
}

export function persistLanguage(lng: Language): void {
  try {
    localStorage.setItem(STORAGE_KEY, lng)
  } catch {
    // Non-critical: the preference simply won't survive a reload.
  }
}

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, ar: { translation: ar } },
  lng: readStoredLanguage(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

export default i18n
