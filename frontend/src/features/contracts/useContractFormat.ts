import { useTranslation } from 'react-i18next'
import { useLanguage } from '../../i18n/useLanguage'
import type { Contract, Lookup } from './api'

const DAY_MS = 24 * 60 * 60 * 1000
const FSI = String.fromCharCode(0x2068) // first-strong isolate
const PDI = String.fromCharCode(0x2069) // pop directional isolate
const NBSP = String.fromCharCode(0xa0) // no-break space

/** Calendar date "2026-12-31" as a local date (no time-zone shift). */
export function parseDay(day: string): Date {
  const [year, month, date] = day.split('-').map(Number)
  return new Date(year, month - 1, date)
}

/** Whole days from today to `day` (negative when it has passed). */
export function daysUntil(day: string): number {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.round((parseDay(day).getTime() - today.getTime()) / DAY_MS)
}

export interface StatusDisplay {
  label: string
  className: string
  note?: string
}

/** Formatting shared by the contract screens, in the current language. */
export function useContractFormat() {
  const { t } = useTranslation()
  const { language } = useLanguage()
  const dateFormat = new Intl.DateTimeFormat(language, { day: 'numeric', month: 'short', year: 'numeric' })

  const name = (lookup: Lookup) => (language === 'ar' ? lookup.name_ar : lookup.name_en)
  const date = (day: string | null | undefined) => (day ? dateFormat.format(parseDay(day)) : '—')
  // Each date of a term stays in one piece: isolated for bidi (FSI … PDI) and with non-breaking spaces, so a long
  // term wraps only at the dash, in English and in Arabic.
  const unbroken = (text: string) => `${FSI}${text.replaceAll(' ', NBSP)}${PDI}`
  const term = (contract: Contract) =>
    `${unbroken(date(contract.start_date))} – ${unbroken(contract.end_date ? date(contract.end_date) : t('contracts.openEnded'))}`

  /** "EGP 2.4M" in lists, "EGP 2,400,000" on the details page. */
  const money = (contract: Contract, compact = false) => {
    if (contract.value_amount === null || contract.value_amount === undefined || !contract.currency)
      return '—'
    const amount = new Intl.NumberFormat(language, {
      notation: compact ? 'compact' : 'standard',
      maximumFractionDigits: 2,
    }).format(Number(contract.value_amount))
    return `${contract.currency} ${amount}`
  }

  /** Status pill as in the design: an active contract ending soon shows as "Expiring". */
  const status = (contract: Contract, expiringSoonDays: number): StatusDisplay => {
    const code = contract.status.code
    if (contract.archived_at) return { label: t('contracts.archived'), className: 'pill pill-grey pill-dot' }
    if (code === 'active' && contract.end_date) {
      const days = daysUntil(contract.end_date)
      if (days >= 0 && days <= expiringSoonDays) {
        return {
          label: t('contracts.expiring'),
          className: 'pill pill-amber pill-dot',
          note: days === 0 ? t('contracts.endsToday') : t('contracts.endsIn', { count: days }),
        }
      }
    }
    const tone = code === 'active' ? 'pill-green' : code === 'draft' ? 'pill-blue' : 'pill-grey'
    return { label: name(contract.status), className: `pill ${tone} pill-dot` }
  }

  /** "Month 10 of 36" and the share of the term that has passed, for contracts with an end date. */
  const progress = (contract: Contract) => {
    if (!contract.end_date) return null
    const start = parseDay(contract.start_date)
    const end = parseDay(contract.end_date)
    const months = Math.max(
      1,
      (end.getFullYear() - start.getFullYear()) * 12 + end.getMonth() - start.getMonth() + 1,
    )
    const now = new Date()
    const elapsed = (now.getFullYear() - start.getFullYear()) * 12 + now.getMonth() - start.getMonth() + 1
    const month = Math.min(Math.max(elapsed, 0), months)
    return { month, months, percent: Math.round((month / months) * 100) }
  }

  return { name, date, term, money, status, progress }
}
