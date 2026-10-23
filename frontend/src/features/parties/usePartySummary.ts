import { useTranslation } from 'react-i18next'
import type { Party } from './api'

// Left-to-right isolate (LRI … PDI): keeps "512-884-201" in order inside Arabic text.
const ltr = (value: string) => `⁦${value}⁩`

/** "Organization · Reg. no. 41872" / "Individual · National ID on file", as in the design's party chips. */
export function usePartySummary() {
  const { t } = useTranslation()
  return (party: Party) => {
    const parts = [t(`partyTypes.${party.party_type}`)]
    if (party.registration_no) parts.push(t('parties.regNoShort', { value: ltr(party.registration_no) }))
    else if (party.tax_no) parts.push(t('parties.taxNoShort', { value: ltr(party.tax_no) }))
    else if (party.national_id) parts.push(t('parties.nationalIdOnFile'))
    else if (party.passport_no) parts.push(t('parties.passportOnFile'))
    return parts.join(' · ')
  }
}
