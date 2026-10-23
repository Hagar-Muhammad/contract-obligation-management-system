import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import type { Me } from '../../api/client'
import { renderApp } from '../../test/renderApp'
import { ADMIN, EMPLOYEE, json, mockApi, signedInAs } from '../../test/mockApi'
import type { Property } from './api'

const PROPERTY_MANAGER: Me = {
  ...EMPLOYEE,
  id: '77777777-7777-7777-7777-777777777777',
  full_name: 'Youssef Ramadan',
  roles: ['property_manager'],
  permissions: ['contract:view', 'party:manage', 'obligation:view', 'report:view'],
  data_scopes: ['assigned_properties'],
}
const NOHA = {
  id: '88888888-8888-8888-8888-888888888888',
  full_name: 'Noha Ahmed',
  email: 'noha@example.com',
}

const property = (overrides: Partial<Property>): Property => ({
  id: crypto.randomUUID(),
  code: 'WM-G14',
  name: 'Westgate Mall · Unit G-14',
  property_type: 'retail',
  address: null,
  city: 'Cairo',
  country: 'Egypt',
  area_sqm: '148.00',
  notes: null,
  managers: [NOHA],
  created_at: '2026-10-20T09:00:00Z',
  updated_at: '2026-10-20T09:00:00Z',
  ...overrides,
})

const WESTGATE = property({ id: '99999999-9999-9999-9999-999999999999' })
const TOWER = property({
  code: 'NC-B',
  name: 'Nile Crest Tower B',
  property_type: 'office',
  area_sqm: null,
  managers: [],
})

const page = (items: Property[]) => json(200, { items, page: 1, page_size: 25, total: items.length })

describe('TC-PROP-01 property register (FR-PROP-01 groundwork)', () => {
  it('lists properties with type, location, area and managers', async () => {
    mockApi({ ...signedInAs(ADMIN), 'GET /api/v1/properties': () => page([TOWER, WESTGATE]) })
    renderApp('/properties')

    const row = (await screen.findByText('Westgate Mall · Unit G-14')).closest('tr')!
    expect(within(row).getByText('WM-G14')).toBeInTheDocument()
    expect(within(row).getByText('Retail')).toBeInTheDocument()
    expect(within(row).getByText('Cairo, Egypt')).toBeInTheDocument()
    expect(within(row).getByText('148 m²')).toBeInTheDocument()
    expect(within(row).getByText('Noha Ahmed')).toBeInTheDocument()
    const tower = screen.getByText('Nile Crest Tower B').closest('tr')!
    expect(within(tower).getByText('No manager')).toBeInTheDocument()
  })

  it('registers a property with an upper-case code and assigned managers', async () => {
    const server = mockApi({
      ...signedInAs(ADMIN),
      'GET /api/v1/properties/assignable-managers': () => json(200, [NOHA]),
      'POST /api/v1/properties': () => json(201, WESTGATE),
      'GET /api/v1/properties': () => page([WESTGATE]),
    })
    renderApp('/properties/new')

    const user = userEvent.setup()
    await user.type(await screen.findByLabelText('Property code'), 'wm-g14')
    await user.click(screen.getByLabelText('Property type'))
    await user.click(await screen.findByTitle('Retail'))
    await user.type(screen.getByLabelText('Name'), 'Westgate Mall · Unit G-14')
    await user.type(screen.getByLabelText('Area'), '148')
    await user.click(screen.getByLabelText('Property managers'))
    await user.click(await screen.findByTitle('Noha Ahmed · noha@example.com'))
    await user.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(server.callsTo('POST', '/api/v1/properties')).toHaveLength(1))
    expect(server.callsTo('POST', '/api/v1/properties')[0].body).toEqual({
      code: 'WM-G14',
      name: 'Westgate Mall · Unit G-14',
      property_type: 'retail',
      area_sqm: 148,
      address: null,
      city: null,
      country: null,
      notes: null,
      manager_ids: [NOHA.id],
    })
  })

  it('shows a Property Manager their assigned property read-only', async () => {
    const server = mockApi({
      ...signedInAs(PROPERTY_MANAGER),
      [`GET /api/v1/properties/${WESTGATE.id}`]: () => json(200, WESTGATE),
    })
    renderApp(`/properties/${WESTGATE.id}`)

    const name = await screen.findByLabelText('Name')
    await waitFor(() => expect(name).toHaveValue('Westgate Mall · Unit G-14'))
    expect(name).toBeDisabled()
    expect(screen.getByText('Noha Ahmed · noha@example.com')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Save' })).not.toBeInTheDocument()
    // Without property:manage the form never asks for the list of assignable managers (it would be 403).
    expect(server.callsTo('GET', '/api/v1/properties/assignable-managers')).toHaveLength(0)
  })

  it('tells a Property Manager when nothing is assigned to them yet', async () => {
    mockApi({ ...signedInAs(PROPERTY_MANAGER), 'GET /api/v1/properties': () => page([]) })
    renderApp('/properties')

    expect(await screen.findByText('No properties are assigned to you yet.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Add property/ })).not.toBeInTheDocument()
  })
})
