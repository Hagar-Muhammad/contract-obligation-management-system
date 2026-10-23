import { useTranslation } from 'react-i18next'
import { daysUntil, useContractFormat } from '../contracts/useContractFormat'
import type { EffectiveStatus, Obligation, Priority } from './api'

/** Repeat choices offered in the form, as RRULEs (BR-08). Anything else is shown as a custom rule. */
export const REPEAT_PRESETS = {
  weekly: 'FREQ=WEEKLY',
  monthly: 'FREQ=MONTHLY',
  quarterly: 'FREQ=MONTHLY;INTERVAL=3',
  half_yearly: 'FREQ=MONTHLY;INTERVAL=6',
  yearly: 'FREQ=YEARLY',
} as const
export type RepeatPreset = keyof typeof REPEAT_PRESETS

export function presetOf(rule: string | null | undefined): RepeatPreset | 'none' | 'custom' {
  if (!rule) return 'none'
  const found = (Object.entries(REPEAT_PRESETS) as [RepeatPreset, string][]).find(
    ([, value]) => value === rule,
  )
  return found ? found[0] : 'custom'
}

const STATUS_PILL: Record<EffectiveStatus, string> = {
  pending: 'pill pill-amber pill-dot',
  in_progress: 'pill pill-blue pill-dot',
  completed: 'pill pill-green pill-dot',
  overdue: 'pill pill-red pill-dot',
  cancelled: 'pill pill-grey pill-dot',
}

const PRIORITY_MARKS: Record<Priority, number> = { low: 0, medium: 1, high: 2, critical: 3 }

/** Formatting shared by the obligation screens (design screen 7). */
export function useObligationFormat() {
  const { t } = useTranslation()
  const { date } = useContractFormat()

  const status = (obligation: Pick<Obligation, 'effective_status'>) => ({
    className: STATUS_PILL[obligation.effective_status],
    label: t(`obligations.statuses.${obligation.effective_status}`),
  })

  /** "in 3 days", "today", "7 days overdue" (BR-04), or nothing for an ongoing duty. */
  const due = (obligation: Pick<Obligation, 'due_date' | 'effective_status'>) => {
    if (!obligation.due_date) return { date: t('obligations.noDeadline'), note: undefined, late: false }
    const days = daysUntil(obligation.due_date)
    const open = obligation.effective_status !== 'completed' && obligation.effective_status !== 'cancelled'
    let note: string | undefined
    if (open && days < 0) note = t('obligations.daysOverdue', { count: -days })
    else if (open && days === 0) note = t('obligations.dueToday')
    else if (open) note = t('obligations.dueIn', { count: days })
    return { date: date(obligation.due_date), note, late: open && days < 0 }
  }

  /** "Monthly", "Quarterly"…, "Repeats" for a custom rule, "One-time" without one. */
  const repeats = (rule: string | null | undefined) => {
    const preset = presetOf(rule)
    return preset === 'none' ? t('obligations.oneTime') : t(`obligations.repeat.${preset}`)
  }

  const priority = (value: Priority) => ({
    marks: '▲'.repeat(PRIORITY_MARKS[value]),
    label: t(`obligations.priorities.${value}`),
    className: `priority priority-${value}`,
  })

  return { status, due, repeats, priority }
}
