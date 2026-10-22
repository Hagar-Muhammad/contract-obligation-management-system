import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { renderApp } from '../../test/renderApp'
import { ADMIN, apiError, json, mockApi, signedInAs } from '../../test/mockApi'
import type { Role, User } from './api'

const role = (code: string, permissions: string[], overrides: Partial<Role> = {}): Role => ({
  code,
  name: code,
  description: '',
  data_scope: 'all',
  permissions,
  scoped_permissions: [],
  ...overrides,
})

const ROLES: Role[] = [
  role('admin', ['contract:view', 'contract:edit', 'user:manage', 'report:view', 'obligation:update']),
  role('legal', ['contract:view', 'contract:edit', 'report:view', 'obligation:update'], {
    scoped_permissions: ['contract:edit'],
  }),
  role('employee', ['contract:view', 'obligation:view', 'report:view'], {
    data_scope: 'assigned_obligations',
    scoped_permissions: ['contract:view'],
  }),
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
const OLD_TIMER: User = {
  ...JANE,
  id: '44444444-4444-4444-4444-444444444444',
  full_name: 'Old Timer',
  is_active: false,
}

const page = (items: User[]) => json(200, { items, page: 1, page_size: 25, total: items.length })
const withRoles = { 'GET /api/v1/roles': () => json(200, ROLES) }

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
      ...withRoles,
      'POST /api/v1/users': () => json(201, JANE),
      'GET /api/v1/users': () => page([JANE]),
    })
    renderApp('/users/new')

    await fillNewUser()

    expect(await screen.findByRole('heading', { name: 'Users & roles' })).toBeInTheDocument()
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
      ...withRoles,
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
      ...withRoles,
      'POST /api/v1/users': () => apiError(409, 'conflict', 'A user with this e-mail already exists.'),
    })
    renderApp('/users/new')

    await fillNewUser()

    expect(await screen.findByText('A user with this email already exists.')).toBeInTheDocument()
  })

  it('requires at least one role', async () => {
    const server = mockApi({ ...signedInAs(ADMIN), ...withRoles })
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
      ...withRoles,
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
  it('deactivates a user from the edit page after confirmation', async () => {
    const server = mockApi({
      ...signedInAs(ADMIN),
      ...withRoles,
      'GET /api/v1/users/:id': () => json(200, JANE),
      'POST /api/v1/users/:id/deactivate': () => json(200, { ...JANE, is_active: false }),
      'GET /api/v1/users': () => page([JANE]),
    })
    renderApp(`/users/${JANE.id}`)

    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: 'Deactivate user' }))
    await user.click(await screen.findByRole('button', { name: 'OK' }))

    await waitFor(() => expect(server.callsTo('POST', `/api/v1/users/${JANE.id}/deactivate`)).toHaveLength(1))
  })

  it('reactivates a deactivated user from the list', async () => {
    const server = mockApi({
      ...signedInAs(ADMIN),
      ...withRoles,
      'GET /api/v1/users': () => page([JANE, OLD_TIMER]),
      'POST /api/v1/users/:id/activate': () => json(200, { ...OLD_TIMER, is_active: true }),
    })
    renderApp('/users')

    const row = (await screen.findByText('Old Timer')).closest('tr')!
    expect(within(row).getByText('Deactivated')).toBeInTheDocument()
    await userEvent.click(within(row).getByRole('button', { name: 'Reactivate' }))

    await waitFor(() =>
      expect(server.callsTo('POST', `/api/v1/users/${OLD_TIMER.id}/activate`)).toHaveLength(1),
    )
  })

  it('lists users with role, scope and status', async () => {
    mockApi({ ...signedInAs(ADMIN), ...withRoles, 'GET /api/v1/users': () => page([JANE, OLD_TIMER]) })
    renderApp('/users')

    const janeRow = (await screen.findByText('Jane Doe')).closest('tr')!
    expect(within(janeRow).getByText('Legal User')).toBeInTheDocument()
    expect(within(janeRow).getByText('All contracts')).toBeInTheDocument()
    expect(within(janeRow).getByText('Active')).toBeInTheDocument()
    expect(within(janeRow).getByRole('button', { name: 'Edit' })).toBeInTheDocument()
  })
})

describe('TC-AUTH-03 role permissions matrix (SRS 3.2)', () => {
  it('shows full, scoped, limited and no access from the roles API', async () => {
    mockApi({ ...signedInAs(ADMIN), ...withRoles, 'GET /api/v1/users': () => page([JANE]) })
    renderApp('/users')

    const matrix = (await screen.findByRole('heading', { name: 'Role permissions' })).closest('section')!
    const editRow = within(matrix).getByText('Create / edit contracts').closest('tr')!
    // admin ✓, legal Scoped, employee —
    expect(within(editRow).getByLabelText('Full access')).toBeInTheDocument()
    expect(within(editRow).getByText('Scoped')).toBeInTheDocument()
    expect(within(editRow).getByLabelText('No access')).toBeInTheDocument()

    const reportsRow = within(matrix).getByText('View reports').closest('tr')!
    expect(within(reportsRow).getByText('Limited')).toBeInTheDocument()

    const updateRow = within(matrix).getByText('Update assigned obligations').closest('tr')!
    expect(within(updateRow).getByText('View only')).toBeInTheDocument()
  })
})
