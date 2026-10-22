import { useLanguage } from './useLanguage'

/** "5 minutes ago", "yesterday", "in 3 days"… in the current language. */
export function useRelativeTime() {
  const { language } = useLanguage()
  const format = new Intl.RelativeTimeFormat(language, { numeric: 'auto' })
  return (iso: string) => {
    const minutes = Math.round((new Date(iso).getTime() - Date.now()) / 60000)
    if (Math.abs(minutes) < 60) return format.format(minutes, 'minute')
    const hours = Math.round(minutes / 60)
    if (Math.abs(hours) < 24) return format.format(hours, 'hour')
    return format.format(Math.round(hours / 24), 'day')
  }
}
