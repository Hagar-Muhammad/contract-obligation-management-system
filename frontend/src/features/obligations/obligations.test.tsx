import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import type { Me } from '../../api/client'
import { renderApp } from '../../test/renderApp'
import { ADMIN, EMPLOYEE, json, mockApi, signedInAs, type Handler } from '../../test/mockApi'
import type { Contract } from '../contracts/api'
import type { Obligation } from './api'

const MANAGEMENT: Me = {
  ...EMPLOYEE,
  id: '55555555-5555-5555-5555-555555555555',
  full_name: 'Mona Management',
  roles: ['management'],
  permissions: ['contract:view', 'document:view', 'obligation:view', 'report:view', 'report:export'],
  data_scopes: ['all'],
}

const inDays = (days: number) => {
  const date = new Date()
  date.setDate(date.getDate() + days)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

const CONTRACT_REF = { id: 'c1', contract_number: 'CT-2026-0142', title: 'Retail lease — Unit G-14' }

const obligation = (overrides: Partial<Obligation>): Obligation => ({
  id: 'o1',
  contract: CONTRACT_REF,
  title: 'Quarterly rent payment',
  description: 'Rent for the quarter, paid in advance.',
  responsible_party: { id: 'p2', display_name: 'Bloom Café LLC', party_type: 'organization' },
  responsible_user: { id: EMPLOYEE.id, full_name: 'Eve Employee' },
  start_date: null,
  due_date: inDays(3),
  priority: 'high',
  status: 'in_progress',
  effective_status: 'in_progress',
  recurrence_rule: 'FREQ=MONTHLY;INTERVAL=3',
  series_id: 'o1',
  penalty_text: null,
  notes: null,
  completed_at: null,
  cancelled_at: null,
  overdue_at: null,
  evidence_count: 0,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
  ...overrides,
})

const RENT = obligation({})
const INSURANCE = obligation({
  id: 'o2',
  title: 'Provide public liability insurance certificate',
  due_date: inDays(-7),
  priority: 'critical',
  status: 'pending',
  effective_status: 'overdue',
  recurrence_rule: 'FREQ=YEARLY',
  responsible_user: null,
})

const page = <T,>(items: T[]) => json(200, { items, page: 1, page_size: 25, total: items.length })
const routes = (extra: Record<string, Handler> = {}): Record<string, Handler> => ({
  'GET /api/v1/obligations': () => page([INSURANCE, RENT]),
  'GET /api/v1/obligations/counts': () =>
    json(200, {
      open: 342,
      overdue: 14,
      due_this_week: 23,
      in_progress: 86,
      pending: 242,
      completed: 512,
      cancelled: 9,
    }),
  'GET /api/v1/obligations/o1': () => json(200, RENT),
  'GET /api/v1/obligations/o1/activity': () => json(200, []),
  'GET /api/v1/obligations/o1/evidence': () => json(200, []),
  'GET /api/v1/contracts': () => page([]),
  'GET /api/v1/users/directory': () => json(200, []),
  'GET /api/v1/documents/limits': () =>
    json(200, { max_bytes: 20971520, allowed_types: ['pdf', 'docx', 'png', 'jpg'] }),
  ...extra,
})

describe('TC-OBL-07 obligations list (FR-OBL-07, FR-OBL-05)', () => {
  it('shows who owns each obligation, when it is due and how it stands', async () => {
    mockApi({ ...signedInAs(ADMIN), ...routes() })
    renderApp('/obligations')

    const late = (await screen.findByText('Provide public liability insurance certificate')).closest('tr')!
    expect(within(late).getByText('Overdue')).toBeInTheDocument()
    expect(within(late).getByText('7 days overdue')).toBeInTheDocument()
    expect(within(late).getByText('Critical')).toBeInTheDocument()
    expect(within(late).getByText(/CT-2026-0142/)).toBeInTheDocument()
    const rent = screen.getByText('Quarterly rent payment').closest('tr')!
    expect(within(rent).getByText('in 3 days')).toBeInTheDocument()
    expect(within(rent).getByText('Eve Employee')).toBeInTheDocument()
    expect(within(rent).getByText(/· Quarterly/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Overdue 14/ })).toBeInTheDocument()
  })

  it('sends the status chip, search and filters to the server', async () => {
    const server = mockApi({ ...signedInAs(ADMIN), ...routes() })
    renderApp('/obligations?contract=c1')

    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: /Overdue 14/ }))
    await user.type(screen.getByLabelText('Search obligations'), 'rent')
    await user.click(screen.getByLabelText('Only mine'))
    await waitFor(() => {
      const last = server.callsTo('GET', '/api/v1/obligations').at(-1)!.search
      expect(last).toContain('view=overdue')
      expect(last).toContain('q=rent')
      expect(last).toContain('mine=true')
      expect(last).toContain('contract_id=c1')
    })
  })
})

describe('TC-OBL-04 status update (FR-OBL-04)', () => {
  it('saves a new status with a note for the audit trail', async () => {
    const server = mockApi({
      ...signedInAs(ADMIN),
      ...routes({ 'POST /api/v1/obligations/o1/status': () => json(200, { ...RENT, status: 'completed' }) }),
    })
    renderApp('/obligations/o1')

    const panel = await screen.findByRole('complementary', { name: 'Obligation details' })
    expect(await within(panel).findByRole('heading', { name: 'Quarterly rent payment' })).toBeInTheDocument()
    const user = userEvent.setup()
    await user.click(within(panel).getByText('Completed'))
    await user.type(within(panel).getByLabelText('Note'), 'Paid on the 2nd')
    await user.click(within(panel).getByRole('button', { name: 'Save update' }))

    await waitFor(() => expect(server.callsTo('POST', '/api/v1/obligations/o1/status')).toHaveLength(1))
    expect(server.callsTo('POST', '/api/v1/obligations/o1/status')[0].body).toEqual({
      status: 'completed',
      note: 'Paid on the 2nd',
    })
  })

  it('lets an employee update the status of their obligation but not edit its details', async () => {
    mockApi({ ...signedInAs(EMPLOYEE), ...routes() })
    renderApp('/obligations/o1')

    const panel = await screen.findByRole('complementary', { name: 'Obligation details' })
    expect(await within(panel).findByRole('button', { name: 'Save update' })).toBeInTheDocument()
    expect(within(panel).queryByRole('button', { name: /Edit details/ })).not.toBeInTheDocument()
  })

  it('is read-only for management', async () => {
    mockApi({ ...signedInAs(MANAGEMENT), ...routes() })
    renderApp('/obligations/o1')

    const panel = await screen.findByRole('complementary', { name: 'Obligation details' })
    expect(await within(panel).findByText('Rent for the quarter, paid in advance.')).toBeInTheDocument()
    expect(within(panel).queryByRole('button', { name: 'Save update' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /New obligation/ })).not.toBeInTheDocument()
  })
})

describe('TC-OBL-01 new obligation (FR-OBL-01..03, FR-OBL-06)', () => {
  const contract: Contract = {
    id: 'c1',
    contract_number: 'CT-2026-0142',
    title: 'Retail lease — Unit G-14',
    contract_type: { code: 'lease', name_en: 'Lease', name_ar: 'إيجار' },
    status: { code: 'active', name_en: 'Active', name_ar: 'سارٍ', next_codes: [] },
    description: null,
    start_date: '2026-01-01',
    end_date: null,
    value_amount: null,
    currency: null,
    renewal_date: null,
    parties: [
      { id: 'p1', display_name: 'Nile Crest Properties', party_type: 'organization', role: 'landlord' },
      { id: 'p2', display_name: 'Bloom Café LLC', party_type: 'organization', role: 'tenant' },
    ],
    properties: [],
    archived_at: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    created_by: null,
    updated_by: null,
    obligations: { open: 0, overdue: 0 },
  }

  it('creates a quarterly obligation for one of the contract’s parties', async () => {
    const server = mockApi({
      ...signedInAs(ADMIN),
      ...routes({
        'GET /api/v1/contracts/c1': () => json(200, contract),
        'POST /api/v1/obligations': () => json(201, RENT),
      }),
    })
    renderApp('/obligations/new?contract=c1')

    const user = userEvent.setup()
    await user.type(await screen.findByLabelText('Title'), 'Quarterly rent payment')
    await user.type(screen.getByLabelText('Description'), 'Rent for the quarter.')
    await user.click(screen.getByLabelText('Party'))
    await user.click(await screen.findByTitle('Bloom Café LLC · Tenant'))
    await user.click(screen.getByLabelText('Due'))
    // Tab commits the typed date; Enter would submit the whole form, as in any HTML form.
    await user.type(screen.getByLabelText('Due'), '2026-12-25{Tab}')
    await user.click(screen.getByLabelText('Repeats'))
    await user.click(await screen.findByTitle('Quarterly'))
    await user.click(screen.getByRole('button', { name: 'Create obligation' }))

    await waitFor(() => expect(server.callsTo('POST', '/api/v1/obligations')).toHaveLength(1))
    expect(server.callsTo('POST', '/api/v1/obligations')[0].body).toEqual({
      contract_id: 'c1',
      title: 'Quarterly rent payment',
      description: 'Rent for the quarter.',
      responsible_party_id: 'p2',
      responsible_user_id: null,
      start_date: null,
      due_date: '2026-12-25',
      priority: 'medium',
      status: 'pending',
      recurrence_rule: 'FREQ=MONTHLY;INTERVAL=3',
      penalty_text: null,
      notes: null,
    })
  })
})
