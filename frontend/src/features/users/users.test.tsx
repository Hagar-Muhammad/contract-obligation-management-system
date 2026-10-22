import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { renderApp } from '../../test/renderApp'
import { ADMIN, apiError, json, mockApi, signedInAs } from '../../test/mockApi'
import type { Role, User } from './api'

const ROLES: Role[] = [
  { code: 'admin', name: 'Administrator', description: '', data_scope: 'all', permissions: [] },
  { code: 'legal', name: 'Legal User', description: '', data_scope: 'all', permissions: [] },
]

const JANE: User = {
  id: '33333333-3333-3333-3333-333333333333',
  email: 'jane@example.com',
  full_name: 'Jane Doe',
  preferred_language: 'en',
  is_active: true,
  role_codes: ['legal'],
  last_login_at: null,
  created_at: '2026-10-22T09:00:00Z',
  updated_at: '2026-10-22T09:00:00Z',
}

const page = (items: User[]) => json(200, { items, page: 1, page_size: 25, total: items.length })

async function fillNewUser() {
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('Full name'), 'Jane Doe')
  await user.type(screen.getByLabelText('Email'), 'jane@example.com')
  await user.type(screen.getByLabelText('Password'), 'Str0ng-Password')
  await user.click(screen.getByLabelText('Roles'))
  await user.click(await screen.findByTitle('Legal User'))
  await user.click(screen.getByRole('button', { name: 'Save' }))
}

describe('TC-USER-01 create user (FR-USER-01)', () => {
  it('creates a user with the selected role', async () => {
    const server = mockApi({
      ...signedInAs(ADMIN),
      'GET /api/v1/roles': () => json(200, ROLES),
      'POST /api/v1/users': () => json(201, JANE),
      'GET /api/v1/users': () => page([JANE]),
    })
    renderApp('/users/new')

    await fillNewUser()

    expect(await screen.findByRole('heading', { name: 'Users' })).toBeInTheDocument()
    expect(server.callsTo('POST', '/api/v1/users')[0].body).toEqual({
      full_name: 'Jane Doe',
      email: 'jane@example.com',
      password: 'Str0ng-Password',
      role_codes: ['legal'],
      preferred_language: 'en',
    })
  })

  it('shows server validation errors next to the field (NFR-UX-02)', async () => {
    mockApi({
      ...signedInAs(ADMIN),
      'GET /api/v1/roles': () => json(200, ROLES),
      'POST /api/v1/users': () =>
        apiError(422, 'validation_error', 'Request validation failed.', [
          { field: 'body.email', message: 'value is not a valid email address', type: 'value_error' },
        ]),
    })
    renderApp('/users/new')

    await fillNewUser()

    expect(await screen.findByText('value is not a valid email address')).toBeInTheDocument()
  })

  it('explains a duplicate email', async () => {
    mockApi({
      ...signedInAs(ADMIN),
      'GET /api/v1/roles': () => json(200, ROLES),
      'POST /api/v1/users': () => apiError(409, 'conflict', 'A user with this e-mail already exists.'),
    })
    renderApp('/users/new')

    await fillNewUser()

    expect(await screen.findByText('A user with this email already exists.')).toBeInTheDocument()
  })

  it('requires at least one role', async () => {
    const server = mockApi({ ...signedInAs(ADMIN), 'GET /api/v1/roles': () => json(200, ROLES) })
    renderApp('/users/new')

    await userEvent.click(await screen.findByRole('button', { name: 'Save' }))

    expect(await screen.findByText('Select at least one role.')).toBeInTheDocument()
    expect(server.callsTo('POST', '/api/v1/users')).toHaveLength(0)
  })
})

describe('TC-USER-02 update user (FR-USER-02)', () => {
  it('loads the user and saves changes', async () => {
    const server = mockApi({
      ...signedInAs(ADMIN),
      'GET /api/v1/roles': () => json(200, ROLES),
      'GET /api/v1/users/:id': () => json(200, JANE),
      'PATCH /api/v1/users/:id': () => json(200, { ...JANE, full_name: 'Jane Smith' }),
      'GET /api/v1/users': () => page([JANE]),
    })
    renderApp(`/users/${JANE.id}`)

    const user = userEvent.setup()
    const name = await screen.findByDisplayValue('Jane Doe')
    await user.clear(name)
    await user.type(name, 'Jane Smith')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(server.callsTo('PATCH', `/api/v1/users/${JANE.id}`)).toHaveLength(1))
    expect(server.callsTo('PATCH', `/api/v1/users/${JANE.id}`)[0].body).toMatchObject({
      full_name: 'Jane Smith',
      role_codes: ['legal'],
    })
  })
})

describe('TC-USER-03 deactivate user (FR-USER-03)', () => {
  it('deactivates a user after confirmation', async () => {
    const server = mockApi({
      ...signedInAs(ADMIN),
      'GET /api/v1/users': () => page([JANE]),
      'POST /api/v1/users/:id/deactivate': () => json(200, { ...JANE, is_active: false }),
    })
    renderApp('/users')

    const user = userEvent.setup()
    const row = (await screen.findByText('Jane Doe')).closest('tr')!
    await user.click(within(row).getByRole('button', { name: 'Deactivate' }))
    await user.click(await screen.findByRole('button', { name: 'OK' }))

    await waitFor(() => expect(server.callsTo('POST', `/api/v1/users/${JANE.id}/deactivate`)).toHaveLength(1))
  })

  it('lists users with their roles and status', async () => {
    mockApi({
      ...signedInAs(ADMIN),
      'GET /api/v1/users': () => page([JANE, { ...JANE, id: 'x', full_name: 'Old Timer', is_active: false }]),
    })
    renderApp('/users')

    const oldRow = (await screen.findByText('Old Timer')).closest('tr')!
    expect(within(oldRow).getByText('Inactive')).toBeInTheDocument()
    expect(within(oldRow).getByRole('button', { name: 'Activate' })).toBeInTheDocument()
    const janeRow = screen.getByText('Jane Doe').closest('tr')!
    expect(within(janeRow).getByText('Legal User')).toBeInTheDocument()
  })
})
