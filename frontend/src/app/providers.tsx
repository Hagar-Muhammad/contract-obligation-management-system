import { QueryClientProvider, type QueryClient } from '@tanstack/react-query'
import { App as AntApp, ConfigProvider, type ThemeConfig } from 'antd'
import arEG from 'antd/locale/ar_EG'
import enUS from 'antd/locale/en_US'
import { useState, type ReactNode } from 'react'
import { AuthProvider } from '../auth/AuthProvider'
import { useLanguage } from '../i18n/useLanguage'
import { createQueryClient } from './queryClient'

const ANTD_LOCALES = { en: enUS, ar: arEG } as const

/** ConTrack brand colours (docs/brand/README.md). */
const THEME: ThemeConfig = {
  token: { colorPrimary: '#1D4ED8', colorSuccess: '#059669', colorLink: '#1D4ED8' },
  components: { Layout: { headerBg: '#0B2545' } },
}

export function AppProviders({ children, queryClient }: { children: ReactNode; queryClient?: QueryClient }) {
  const [client] = useState(() => queryClient ?? createQueryClient())
  const { language, direction } = useLanguage()
  return (
    <ConfigProvider direction={direction} locale={ANTD_LOCALES[language]} theme={THEME}>
      <AntApp>
        <QueryClientProvider client={client}>
          <AuthProvider>{children}</AuthProvider>
        </QueryClientProvider>
      </AntApp>
    </ConfigProvider>
  )
}
