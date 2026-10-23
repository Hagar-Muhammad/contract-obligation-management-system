import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import type { Me } from '../../api/client'
import { renderApp } from '../../test/renderApp'
import { ADMIN, EMPLOYEE, apiError, json, mockApi, signedInAs } from '../../test/mockApi'
import type { Party } from './api'

const MANAGEMENT: Me = {
  ...EMPLOYEE,
  id: '55555555-5555-5555-5555-555555555555',
  full_name: 'Mona Management',
  roles: ['management'],
  permissions: ['contract:view', 'document:view', 'obligation:view', 'report:view', 'report:export'],
  data_scopes: ['all'],
}

const party = (overrides: Partial<Party>): Party => ({
  id: crypto.randomUUID(),
  party_type: 'organization',
  display_name: 'Nile Crest Properties',
  national_id: null,
  passport_no: null,
  registration_no: '41872',
  tax_no: null,
  email: 'leasing@nilecrest.example.com',
  phone: '+20 2 2735 0000',
  address: null,
  notes: null,
  created_at: '2026-10-20T09:00:00Z',
  updated_at: '2026-10-20T09:00:00Z',
  ...overrides,
})

const NILE = party({ id: '66666666-6666-6666-6666-666666666666' })
const HANY = party({
  party_type: 'individual',
  display_name: 'Hany Fawzy',
  registration_no: null,
  national_id: '28501011234567',
  email: null,
  phone: null,
})

const page = (items: Party[]) => json(200, { items, page: 1, page_size: 25, total: items.length })

describe('TC-PARTY-01 parties list (FR-PARTY-01)', () => {
  it('lists parties with their type and main identifier, without exposing personal ID numbers', async () => {
    mockApi({ ...signedInAs(ADMIN), 'GET /api/v1/parties': () => page([NILE, HANY]) })
    renderApp('/parties')

    expect(await screen.findByRole('heading', { name: 'Parties' })).toBeInTheDocument()
    // The number is wrapped in left-to-right isolate marks so it keeps its order in Arabic.
    expect(await screen.findByText('Organization · Reg. no. ⁦41872⁩')).toBeInTheDocument()
    expect(screen.getByText('Individual · National ID on file')).toBeInTheDocument()
    expect(screen.queryByText('28501011234567')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Hany Fawzy/ })).toHaveAttribute('href', `/parties/${HANY.id}`)
    expect(screen.getByRole('button', { name: /Add party/ })).toBeInTheDocument()
  })

  it('sends search and type filters to the server', async () => {
    const server = mockApi({ ...signedInAs(ADMIN), 'GET /api/v1/parties': () => page([HANY]) })
    renderApp('/parties')

    const user = userEvent.setup()
    await user.type(await screen.findByLabelText('Search by name, email, phone or ID number'), 'hany')
    await user.click(screen.getByText('Individuals'))
    await waitFor(() => {
      const last = server.callsTo('GET', '/api/v1/parties').at(-1)!
      expect(last.search).toContain('q=hany')
      expect(last.search).toContain('party_type=individual')
    })
  })

  it('explains an empty list to users who only see parties of their own work', async () => {
    mockApi({ ...signedInAs(EMPLOYEE), 'GET /api/v1/parties': () => page([]) })
    renderApp('/parties')

    expect(
      await screen.findByText('Parties appear here once you work on contracts they belong to.'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Add party/ })).not.toBeInTheDocument()
  })
})

describe('TC-PARTY-02 party form (FR-PARTY-02)', () => {
  it('creates an individual with only the fields of that type', async () => {
    const server = mockApi({
      ...signedInAs(ADMIN),
      'POST /api/v1/parties': () => json(201, HANY),
      'GET /api/v1/parties': () => page([HANY]),
    })
    renderApp('/parties/new')

    const user = userEvent.setup()
    await user.click(await screen.findByText('Individual'))
    await user.type(screen.getByLabelText('Full name'), 'Hany Fawzy')
    await user.type(screen.getByLabelText('National ID'), '28501011234567')
    expect(screen.queryByLabelText('Tax number')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByRole('heading', { name: 'Parties' })).toBeInTheDocument()
    expect(server.callsTo('POST', '/api/v1/parties')[0].body).toEqual({
      party_type: 'individual',
      display_name: 'Hany Fawzy',
      national_id: '28501011234567',
      passport_no: null,
      email: null,
      phone: null,
      address: null,
      notes: null,
    })
  })

  it('shows a duplicate registration number next to its field', async () => {
    mockApi({
      ...signedInAs(ADMIN),
      [`GET /api/v1/parties/${NILE.id}`]: () => json(200, NILE),
      [`PATCH /api/v1/parties/${NILE.id}`]: () =>
        apiError(409, 'conflict', 'Copy Co already has this number.', [
          { field: 'body.registration_no', message: 'Already recorded for Copy Co.' },
        ]),
    })
    renderApp(`/parties/${NILE.id}`)

    const user = userEvent.setup()
    const regNo = await screen.findByLabelText('Commercial registration number')
    await waitFor(() => expect(regNo).toHaveValue('41872'))
    await user.clear(regNo)
    await user.type(regNo, '99')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByText('Already recorded for Copy Co.')).toBeInTheDocument()
  })

  it('is read-only for users who cannot manage parties', async () => {
    mockApi({ ...signedInAs(MANAGEMENT), [`GET /api/v1/parties/${NILE.id}`]: () => json(200, NILE) })
    renderApp(`/parties/${NILE.id}`)

    const name = await screen.findByLabelText('Company name')
    await waitFor(() => expect(name).toHaveValue('Nile Crest Properties'))
    expect(name).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Save' })).not.toBeInTheDocument()
  })
})
