import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Me } from '../../api/client'
import { renderApp } from '../../test/renderApp'
import { ADMIN, EMPLOYEE, apiError, json, mockApi, signedInAs, type Handler } from '../../test/mockApi'
import type { Contract } from '../contracts/api'
import type { ContractDocument } from './api'

const MANAGEMENT: Me = {
  ...EMPLOYEE,
  id: '55555555-5555-5555-5555-555555555555',
  full_name: 'Mona Management',
  roles: ['management'],
  permissions: ['contract:view', 'document:view', 'obligation:view', 'report:view', 'report:export'],
  data_scopes: ['all'],
}

const CONTRACT: Contract = {
  id: 'c0000000-0000-0000-0000-000000000001',
  contract_number: 'CT-2026-0142',
  title: 'Retail lease — Unit G-14',
  contract_type: { code: 'lease', name_en: 'Lease', name_ar: 'إيجار' },
  status: { code: 'active', name_en: 'Active', name_ar: 'سارٍ', next_codes: ['expired', 'terminated'] },
  description: null,
  start_date: '2026-01-01',
  end_date: '2028-12-31',
  value_amount: null,
  currency: null,
  renewal_date: null,
  parties: [
    { id: 'p1', display_name: 'Nile Crest Properties', party_type: 'organization', role: 'landlord' },
  ],
  properties: [],
  archived_at: null,
  created_at: '2025-12-04T10:00:00Z',
  updated_at: '2026-10-18T10:00:00Z',
  created_by: null,
  updated_by: null,
  obligations: { open: 0, overdue: 0 },
}

const LEASE_PDF: ContractDocument = {
  id: 'd0000000-0000-0000-0000-000000000001',
  contract_id: CONTRACT.id,
  obligation_id: null,
  kind: 'contract',
  original_filename: 'Lease_G14_signed.pdf',
  file_type: 'pdf',
  mime_type: 'application/pdf',
  size_bytes: 2_516_582,
  sha256: 'a'.repeat(64),
  uploaded_by: { id: ADMIN.id, full_name: 'Noha Ahmed' },
  uploaded_at: '2025-12-04T10:00:00Z',
}
const ANNEX_DOCX: ContractDocument = {
  ...LEASE_PDF,
  id: 'd0000000-0000-0000-0000-000000000002',
  kind: 'annex',
  original_filename: 'Annex_A_floorplan.docx',
  file_type: 'docx',
  mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  size_bytes: 880_640,
}

const routes = (
  contract: Contract = CONTRACT,
  extra: Record<string, Handler> = {},
): Record<string, Handler> => ({
  [`GET /api/v1/contracts/${contract.id}`]: () => json(200, contract),
  [`GET /api/v1/contracts/${contract.id}/activity`]: () => json(200, []),
  [`GET /api/v1/contracts/${contract.id}/documents`]: () => json(200, [LEASE_PDF, ANNEX_DOCX]),
  'GET /api/v1/contracts/defaults': () =>
    json(200, { next_number: 'CT-2026-0152', default_currency: 'EGP', expiring_soon_days: 60 }),
  'GET /api/v1/contract-statuses': () => json(200, []),
  'GET /api/v1/documents/limits': () =>
    json(200, { max_bytes: 20 * 1024 * 1024, allowed_types: ['pdf', 'docx', 'png', 'jpg'] }),
  ...extra,
})

const fileInput = () => document.querySelector<HTMLInputElement>('.ant-modal input[type=file]')!

beforeEach(() => {
  vi.stubGlobal(
    'URL',
    Object.assign(URL, { createObjectURL: vi.fn(() => 'blob:doc'), revokeObjectURL: vi.fn() }),
  )
})
afterEach(() => vi.restoreAllMocks())

describe('TC-DOC-05 documents on the contract page (FR-DOC-05)', () => {
  it('lists each document with its size, kind and upload date', async () => {
    mockApi({ ...signedInAs(ADMIN), ...routes() })
    renderApp(`/contracts/${CONTRACT.id}`)

    const lease = (await screen.findByText('Lease_G14_signed.pdf')).closest('li')!
    expect(within(lease).getByText('2.4 MB · Original · Dec 4, 2025')).toBeInTheDocument()
    expect(within(lease).getByText('PDF')).toBeInTheDocument()
    const annex = screen.getByText('Annex_A_floorplan.docx').closest('li')!
    expect(within(annex).getByText('860 KB · Annex · Dec 4, 2025')).toBeInTheDocument()
  })
})

describe('TC-DOC-03 download (FR-DOC-03)', () => {
  it('downloads the original through the API with the user’s token', async () => {
    const server = mockApi({
      ...signedInAs(ADMIN),
      ...routes(),
      [`GET /api/v1/documents/${ANNEX_DOCX.id}/download`]: () =>
        new Response(new Blob(['PK']), { status: 200, headers: { 'Content-Type': ANNEX_DOCX.mime_type } }),
    })
    renderApp(`/contracts/${CONTRACT.id}`)

    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: 'Download Annex_A_floorplan.docx' }))

    await waitFor(() =>
      expect(server.callsTo('GET', `/api/v1/documents/${ANNEX_DOCX.id}/download`)).toHaveLength(1),
    )
    expect(server.callsTo('GET', `/api/v1/documents/${ANNEX_DOCX.id}/download`)[0].authorization).toMatch(
      /^Bearer /,
    )
    expect(URL.createObjectURL).toHaveBeenCalled()
  })
})

describe('TC-DOC-01 / TC-DOC-04 upload (FR-DOC-01, FR-DOC-04)', () => {
  it('uploads the chosen file with its kind', async () => {
    const server = mockApi({
      ...signedInAs(ADMIN),
      ...routes(CONTRACT, {
        [`POST /api/v1/contracts/${CONTRACT.id}/documents`]: () => json(201, LEASE_PDF),
      }),
    })
    renderApp(`/contracts/${CONTRACT.id}`)

    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: /Upload/ }))
    const append = vi.spyOn(FormData.prototype, 'append')
    const chosen = new File(['%PDF-1.7'], 'Amendment 1.pdf', { type: 'application/pdf' })
    await user.upload(fileInput(), chosen)
    await user.click(screen.getByLabelText('Document type'))
    await user.click(await screen.findByTitle('Amendment'))
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Upload' }))

    await waitFor(() =>
      expect(server.callsTo('POST', `/api/v1/contracts/${CONTRACT.id}/documents`)).toHaveLength(1),
    )
    const body = String(server.callsTo('POST', `/api/v1/contracts/${CONTRACT.id}/documents`)[0].body)
    // jsdom's File does not survive Node's multipart encoding, so check what the app adds to the form.
    expect(append).toHaveBeenCalledWith('file', chosen, 'Amendment 1.pdf')
    expect(body).toMatch(/name="kind"\s+amendment/)
    expect(await screen.findByText('Amendment 1.pdf uploaded.')).toBeInTheDocument()
  })

  it('refuses an unsupported file before uploading it', async () => {
    const server = mockApi({ ...signedInAs(ADMIN), ...routes() })
    renderApp(`/contracts/${CONTRACT.id}`)

    const user = userEvent.setup({ applyAccept: false })
    await user.click(await screen.findByRole('button', { name: /Upload/ }))
    await user.upload(fileInput(), new File(['MZ'], 'setup.exe', { type: 'application/octet-stream' }))

    expect(
      await screen.findByText('This file type is not supported. Upload PDF, DOCX, PNG, JPG.'),
    ).toBeInTheDocument()
    expect(within(screen.getByRole('dialog')).getByRole('button', { name: 'Upload' })).toBeDisabled()
    expect(server.callsTo('POST', `/api/v1/contracts/${CONTRACT.id}/documents`)).toHaveLength(0)
  })

  it('shows the server’s reason when it refuses a file', async () => {
    mockApi({
      ...signedInAs(ADMIN),
      ...routes(CONTRACT, {
        [`POST /api/v1/contracts/${CONTRACT.id}/documents`]: () =>
          apiError(
            415,
            'unsupported_media_type',
            'This file type is not supported. Upload PDF, DOCX, PNG, JPG.',
          ),
      }),
    })
    renderApp(`/contracts/${CONTRACT.id}`)

    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: /Upload/ }))
    await user.upload(fileInput(), new File(['not really'], 'renamed.pdf', { type: 'application/pdf' }))
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Upload' }))

    expect(
      await screen.findByText('This file type is not supported. Upload PDF, DOCX, PNG, JPG.'),
    ).toBeInTheDocument()
  })

  it('offers no upload to read-only users or on archived contracts', async () => {
    mockApi({ ...signedInAs(MANAGEMENT), ...routes() })
    const { unmount } = renderApp(`/contracts/${CONTRACT.id}`)
    expect(await screen.findByText('Lease_G14_signed.pdf')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Upload/ })).not.toBeInTheDocument()
    unmount()

    const archived = { ...CONTRACT, archived_at: '2026-10-20T00:00:00Z' }
    mockApi({ ...signedInAs(ADMIN), ...routes(archived) })
    renderApp(`/contracts/${CONTRACT.id}`)
    expect(await screen.findByText('Lease_G14_signed.pdf')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Upload/ })).not.toBeInTheDocument()
  })
})
