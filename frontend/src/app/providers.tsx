import { QueryClientProvider, type QueryClient } from '@tanstack/react-query'
import { App as AntApp, ConfigProvider, type ThemeConfig } from 'antd'
import arEG from 'antd/locale/ar_EG'
import enUS from 'antd/locale/en_US'
import { useMemo, useState, type ReactNode } from 'react'
import { AuthProvider } from '../auth/AuthProvider'
import { useLanguage } from '../i18n/useLanguage'
import { createQueryClient } from './queryClient'

const ANTD_LOCALES = { en: enUS, ar: arEG } as const

const LATIN_FONT =
  "'Manrope Variable', 'IBM Plex Sans Arabic', system-ui, -apple-system, 'Segoe UI', sans-serif"
const ARABIC_FONT =
  "'IBM Plex Sans Arabic', 'Manrope Variable', system-ui, -apple-system, 'Segoe UI', sans-serif"

/** ConTrack design tokens (docs/design/ConTrack-UI.pdf, docs/brand/README.md). */
function theme(direction: 'ltr' | 'rtl'): ThemeConfig {
  return {
    token: {
      colorPrimary: '#2563EB',
      colorLink: '#2563EB',
      colorSuccess: '#16A34A',
      colorWarning: '#D97706',
      colorError: '#DC2626',
      colorText: '#0F172A',
      colorTextSecondary: '#64748B',
      colorBorder: '#D6DCE5',
      colorBorderSecondary: '#E5E9F0',
      colorBgLayout: '#F4F6FA',
      borderRadius: 8,
      fontFamily: direction === 'rtl' ? ARABIC_FONT : LATIN_FONT,
    },
    components: {
      Layout: { siderBg: '#0F1B2D', headerBg: '#FFFFFF', bodyBg: '#F4F6FA' },
      Table: { headerBg: '#F8FAFC', headerColor: '#64748B', headerSplitColor: 'transparent' },
      Button: { fontWeight: 600 },
    },
  }
}

export function AppProviders({ children, queryClient }: { children: ReactNode; queryClient?: QueryClient }) {
  const [client] = useState(() => queryClient ?? createQueryClient())
  const { language, direction } = useLanguage()
  const themeConfig = useMemo(() => theme(direction), [direction])
  return (
    <ConfigProvider direction={direction} locale={ANTD_LOCALES[language]} theme={themeConfig}>
      <AntApp>
        <QueryClientProvider client={client}>
          <AuthProvider>{children}</AuthProvider>
        </QueryClientProvider>
      </AntApp>
    </ConfigProvider>
  )
}
