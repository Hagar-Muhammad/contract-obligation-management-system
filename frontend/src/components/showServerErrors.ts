import type { FormInstance } from 'antd'
import type { MessageInstance } from 'antd/es/message/interface'
import type { TFunction } from 'i18next'
import { ApiError } from '../api/errors'

/**
 * Show a failed save next to the inputs the server named (NFR-UX-02), or as a message when it named none.
 * Anything that is not an API error is re-thrown for the error boundary.
 */
export function showServerErrors<Values>(
  err: unknown,
  form: FormInstance<Values>,
  message: MessageInstance,
  t: TFunction,
  overrides: Record<string, string> = {},
): void {
  if (!(err instanceof ApiError)) throw err
  const entries = Object.entries({ ...err.fieldErrors(), ...overrides })
  if (entries.length) {
    form.setFields(entries.map(([name, error]) => ({ name: name as never, errors: [error] })))
  } else {
    message.error(err.message || t('errors.generic'))
  }
}
