import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import type { Me } from '../../api/client'
import { renderApp } from '../../test/renderApp'
import { ADMIN, EMPLOYEE, apiError, json, mockApi, signedInAs, type Handler } from '../../test/mockApi'
import type { Party } from '../parties/api'
import type { Contract, ContractStatus, Lookup } from './api'

const MANAGEMENT: Me = {
  ...EMPLOYEE,
  id: '55555555-5555-5555-5555-555555555555',
  full_name: 'Mona Management',
  roles: ['management'],
  permissions: ['contract:view', 'document:view', 'obligation:view', 'report:view', 'report:export'],
  data_scopes: ['all'],
}

const LEASE: Lookup = { code: 'lease', name_en: 'Lease', name_ar: 'إيجار' }
const SERVICE: Lookup = {
  code: 'service_maintenance',
  name_en: 'Service / Maintenance',
  name_ar: 'خدمات / صيانة',
}
const STATUSES: ContractStatus[] = [
  { code: 'draft', name_en: 'Draft', name_ar: 'مسودة', next_codes: ['active', 'cancelled'] },
  { code: 'active', name_en: 'Active', name_ar: 'سارٍ', next_codes: ['expired', 'terminated'] },
  { code: 'expired', name_en: 'Expired', name_ar: 'منتهٍ', next_codes: [] },
  { code: 'terminated', name_en: 'Terminated', name_ar: 'مفسوخ', next_codes: [] },
  { code: 'cancelled', name_en: 'Cancelled', name_ar: 'ملغى', next_codes: [] },
]

const inDays = (days: number) => {
  const date = new Date()
  date.setDate(date.getDate() + days)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

const contract = (overrides: Partial<Contract>): Contract => ({
  id: 'c0000000-0000-0000-0000-000000000001',
  contract_number: 'CT-2026-0142',
  title: 'Retail lease — Unit G-14',
  contract_type: LEASE,
  status: STATUSES[1],
  description: 'Three-year lease of a ground-floor unit for café use.',
  start_date: '2026-01-01',
  end_date: '2028-12-31',
  value_amount: '2400000.00',
  currency: 'EGP',
  renewal_date: '2028-09-30',
  parties: [
    { id: 'p1', display_name: 'Nile Crest Properties', party_type: 'organization', role: 'landlord' },
    { id: 'p2', display_name: 'Bloom Café LLC', party_type: 'organization', role: 'tenant' },
  ],
  properties: [{ id: 'pr1', code: 'WM-G14', name: 'Westgate Mall · Unit G-14', property_type: 'retail' }],
  archived_at: null,
  created_at: '2025-12-04T10:00:00Z',
  updated_at: '2026-10-18T10:00:00Z',
  created_by: { id: ADMIN.id, full_name: 'Hagar Muhammad' },
  updated_by: null,
  obligations: { open: 0, overdue: 0 },
  ...overrides,
})

const LEASE_G14 = contract({})
const HVAC = contract({
  id: 'c0000000-0000-0000-0000-000000000002',
  contract_number: 'CT-2025-0331',
  title: 'Building insurance',
  contract_type: SERVICE,
  end_date: inDays(9),
  parties: [
    {
      id: 'p3',
      display_name: 'Delta Mutual Insurance',
      party_type: 'organization',
      role: 'service_provider',
    },
  ],
  properties: [],
})

const NILE: Party = {
  id: 'p1',
  party_type: 'organization',
  display_name: 'Nile Crest Properties',
  national_id: null,
  passport_no: null,
  registration_no: '41872',
  tax_no: null,
  email: null,
  phone: null,
  address: null,
  notes: null,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
}

const page = <T,>(items: T[]) => json(200, { items, page: 1, page_size: 25, total: items.length })
const lookups: Record<string, Handler> = {
  'GET /api/v1/contract-types': () => json(200, [LEASE, SERVICE]),
  'GET /api/v1/contract-statuses': () => json(200, STATUSES),
  'GET /api/v1/contracts/defaults': () =>
    json(200, { next_number: 'CT-2026-0152', default_currency: 'EGP', expiring_soon_days: 60 }),
  'GET /api/v1/contracts/counts': () =>
    json(200, { active: 128, draft: 14, expiring: 9, ended: 37, archived: 22 }),
  'GET /api/v1/parties': () => page([NILE]),
  'GET /api/v1/properties': () => page([]),
}

describe('TC-CON-03 contracts list (FR-CON-03, FR-SEARCH-01/02)', () => {
  it('shows contracts with type, parties, property, term, value and status, and tab counts', async () => {
    mockApi({ ...signedInAs(ADMIN), ...lookups, 'GET /api/v1/contracts': () => page([LEASE_G14, HVAC]) })
    renderApp('/contracts')

    const row = (await screen.findByText('Retail lease — Unit G-14')).closest('tr')!
    expect(within(row).getByText('CT-2026-0142')).toBeInTheDocument()
    expect(within(row).getByText('Lease')).toBeInTheDocument()
    expect(within(row).getByText('Nile Crest Properties')).toBeInTheDocument()
    expect(within(row).getByText('Bloom Café LLC')).toBeInTheDocument()
    expect(within(row).getByText('Westgate Mall · Unit G-14')).toBeInTheDocument()
    // Each date is wrapped in isolate marks so it stays in one piece in Arabic.
    expect(within(row).getByText('\u2068Jan 1, 2026\u2069 – \u2068Dec 31, 2028\u2069')).toBeInTheDocument()
    expect(within(row).getByText('EGP 2.4M')).toBeInTheDocument()
    expect(within(row).getByText('Active')).toBeInTheDocument()

    const soon = screen.getByText('Building insurance').closest('tr')!
    expect(within(soon).getByText('Expiring')).toBeInTheDocument()
    expect(within(soon).getByText('Ends in 9 days')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Drafts 14/ })).toBeInTheDocument()
  })

  it('asks for archived contracts only on the Archived tab (BR-07) and sends search and sort', async () => {
    const server = mockApi({ ...signedInAs(ADMIN), ...lookups, 'GET /api/v1/contracts': () => page([]) })
    renderApp('/contracts?property=pr1')

    const user = userEvent.setup()
    await waitFor(() => expect(server.callsTo('GET', '/api/v1/contracts').length).toBeGreaterThan(0))
    const first = server.callsTo('GET', '/api/v1/contracts')[0].search
    expect(first).toContain('view=active')
    expect(first).toContain('property_id=pr1') // FR-PROP-02: opened from a property

    await user.click(screen.getByRole('tab', { name: /Archived/ }))
    await user.type(screen.getByLabelText('Number, title, party or property'), 'bloom')
    await user.click(screen.getByLabelText('Sort'))
    await user.click(await screen.findByTitle('Recently updated'))
    await waitFor(() => {
      const last = server.callsTo('GET', '/api/v1/contracts').at(-1)!.search
      expect(last).toContain('view=archived')
      expect(last).toContain('q=bloom')
      expect(last).toContain('sort=-updated_at')
    })
  })

  it('hides create and edit actions from read-only users', async () => {
    mockApi({ ...signedInAs(MANAGEMENT), ...lookups, 'GET /api/v1/contracts': () => page([LEASE_G14]) })
    renderApp('/contracts')

    expect(await screen.findByText('Retail lease — Unit G-14')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /New contract/ })).not.toBeInTheDocument()
  })
})

describe('TC-CON-01 new contract (FR-CON-01, BR-02, BR-03)', () => {
  async function fillRequired(user: ReturnType<typeof userEvent.setup>) {
    await waitFor(() => expect(screen.getByLabelText('Contract number')).toHaveValue('CT-2026-0152'))
    await user.click(screen.getByLabelText('Contract type'))
    await user.click(await screen.findByTitle('Lease'))
    await user.type(screen.getByLabelText('Title'), 'Kiosk lease — Unit K-03')
    await user.click(screen.getByLabelText('Start date'))
    await user.type(screen.getByLabelText('Start date'), '2026-11-01{Enter}')
  }

  it('creates a draft with the suggested number and a party', async () => {
    const server = mockApi({
      ...signedInAs(ADMIN),
      ...lookups,
      'POST /api/v1/contracts': () => json(201, LEASE_G14),
      [`GET /api/v1/contracts/${LEASE_G14.id}`]: () => json(200, LEASE_G14),
      [`GET /api/v1/contracts/${LEASE_G14.id}/activity`]: () => json(200, []),
    })
    renderApp('/contracts/new')

    const user = userEvent.setup()
    await fillRequired(user)
    await user.type(screen.getByLabelText('Contract value'), '180000')
    await user.click(screen.getByLabelText('Search existing parties by name or ID'))
    await user.click(await screen.findByTitle('Nile Crest Properties'))
    expect(screen.getByLabelText('Role of Nile Crest Properties')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Save as draft' }))

    await waitFor(() => expect(server.callsTo('POST', '/api/v1/contracts')).toHaveLength(1))
    expect(server.callsTo('POST', '/api/v1/contracts')[0].body).toEqual({
      contract_number: 'CT-2026-0152',
      title: 'Kiosk lease — Unit K-03',
      type_code: 'lease',
      status_code: 'draft',
      start_date: '2026-11-01',
      end_date: null,
      value_amount: '180000',
      currency: 'EGP',
      renewal_date: null,
      description: null,
      parties: [{ party_id: 'p1', role: 'landlord' }],
      property_ids: [],
    })
    expect(await screen.findByRole('heading', { name: 'Retail lease — Unit G-14' })).toBeInTheDocument()
  })

  it('will not save without a party and counts the fields to fix (BR-02)', async () => {
    const server = mockApi({ ...signedInAs(ADMIN), ...lookups })
    renderApp('/contracts/new')

    const user = userEvent.setup()
    await fillRequired(user)
    await user.click(screen.getByRole('button', { name: 'Create contract' }))

    expect(await screen.findByText('Add at least one party.')).toBeInTheDocument()
    expect(screen.getByText(/1 field needs fixing/)).toBeInTheDocument()
    expect(server.callsTo('POST', '/api/v1/contracts')).toHaveLength(0)
  })

  it('shows a server rule violation next to its field (BR-03)', async () => {
    mockApi({
      ...signedInAs(ADMIN),
      ...lookups,
      'POST /api/v1/contracts': () =>
        apiError(422, 'business_rule_violation', 'End date can’t be earlier than the start date.', [
          { field: 'body.end_date', message: 'End date can’t be earlier than the start date.' },
        ]),
    })
    renderApp('/contracts/new')

    const user = userEvent.setup()
    await fillRequired(user)
    await user.click(screen.getByLabelText('Search existing parties by name or ID'))
    await user.click(await screen.findByTitle('Nile Crest Properties'))
    await user.click(screen.getByRole('button', { name: 'Create contract' }))

    expect(await screen.findByText('End date can’t be earlier than the start date.')).toBeInTheDocument()
  })
})

describe('TC-CON-04 / TC-CON-05 contract details, edit and archive (FR-CON-03..05)', () => {
  const detailRoutes = (extra: Record<string, Handler> = {}): Record<string, Handler> => ({
    ...lookups,
    [`GET /api/v1/contracts/${LEASE_G14.id}`]: () => json(200, LEASE_G14),
    [`GET /api/v1/contracts/${LEASE_G14.id}/activity`]: () =>
      json(200, [
        {
          occurred_at: '2026-10-18T09:42:00Z',
          actor_type: 'user',
          actor: { id: ADMIN.id, full_name: 'Omar Khaled', email: 'omar@example.com' },
          action: 'contract.status_changed',
          changes: { status: ['draft', 'active'] },
        },
        {
          occurred_at: '2025-12-04T14:02:00Z',
          actor_type: 'user',
          actor: { id: ADMIN.id, full_name: 'Hagar Muhammad', email: 'hagar@example.com' },
          action: 'contract.created',
          changes: null,
        },
      ]),
    ...extra,
  })

  it('shows the key facts, parties with roles, properties and activity', async () => {
    mockApi({ ...signedInAs(ADMIN), ...detailRoutes() })
    renderApp(`/contracts/${LEASE_G14.id}`)

    expect(await screen.findByRole('heading', { name: 'Retail lease — Unit G-14' })).toBeInTheDocument()
    expect(screen.getByText('EGP 2,400,000')).toBeInTheDocument()
    expect(screen.getByText('Organization · Landlord')).toBeInTheDocument()
    expect(screen.getByText('Organization · Tenant')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'All contracts for this property' })).toHaveAttribute(
      'href',
      '/contracts?property=pr1',
    )
    expect(await screen.findByText('moved the contract from Draft to Active')).toBeInTheDocument()
    expect(screen.getByText('created the contract')).toBeInTheDocument()
  })

  it('archives after confirmation', async () => {
    const server = mockApi({
      ...signedInAs(ADMIN),
      ...detailRoutes({
        [`POST /api/v1/contracts/${LEASE_G14.id}/archive`]: () =>
          json(200, { ...LEASE_G14, archived_at: '2026-10-23T10:00:00Z' }),
      }),
    })
    renderApp(`/contracts/${LEASE_G14.id}`)

    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: /Archive/ }))
    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: 'Archive' }))
    await waitFor(() =>
      expect(server.callsTo('POST', `/api/v1/contracts/${LEASE_G14.id}/archive`)).toHaveLength(1),
    )
  })

  it('offers only the allowed next statuses when editing (D-17)', async () => {
    mockApi({ ...signedInAs(ADMIN), ...detailRoutes() })
    renderApp(`/contracts/${LEASE_G14.id}/edit`)

    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByLabelText('Title')).toHaveValue('Retail lease — Unit G-14'))
    await user.click(screen.getByLabelText('Status'))
    // The visible options of the open dropdown (Ant Design also renders hidden ones for screen readers).
    await screen.findByTitle('Terminated')
    const options = [...document.querySelectorAll('.ant-select-item-option')].map((o) =>
      o.getAttribute('title'),
    )
    expect(options).toEqual(['Active', 'Expired', 'Terminated'])
  })

  it('is read-only for users who cannot edit or archive', async () => {
    mockApi({ ...signedInAs(MANAGEMENT), ...detailRoutes() })
    renderApp(`/contracts/${LEASE_G14.id}`)

    expect(await screen.findByRole('heading', { name: 'Retail lease — Unit G-14' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Edit/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Archive/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Full audit log' })).not.toBeInTheDocument()
  })
})
