/** The backend's error envelope (docs/api-standards.md §4). */
export interface ApiErrorBody {
  error: {
    code: string
    message: string
    details?: unknown
  }
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: unknown

  constructor(status: number, body: unknown) {
    const envelope = isEnvelope(body) ? body.error : { code: 'unknown_error', message: 'Request failed.' }
    super(envelope.message)
    this.status = status
    this.code = envelope.code
    this.details = envelope.details
  }

  /**
   * Field errors keyed by form field name: `body.email` -> `email`, `body.role_codes.0` -> `role_codes`.
   * Used to show server validation next to the right input (NFR-UX-02).
   */
  fieldErrors(): Record<string, string> {
    if (!Array.isArray(this.details)) return {}
    const result: Record<string, string> = {}
    for (const detail of this.details) {
      if (typeof detail !== 'object' || detail === null || !('field' in detail)) continue
      const [location, name] = String(detail.field).split('.')
      if (location !== 'body' || !name) continue
      result[name] ??= 'message' in detail ? String(detail.message) : this.message
    }
    return result
  }
}

function isEnvelope(body: unknown): body is ApiErrorBody {
  return typeof body === 'object' && body !== null && 'error' in body
}

/** Unwrap an openapi-fetch result, throwing ApiError for non-2xx responses. */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error !== undefined || !result.response.ok) {
    throw new ApiError(result.response.status, result.error)
  }
  return result.data as T
}
