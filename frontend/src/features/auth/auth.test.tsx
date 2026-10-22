import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { api } from '../../api/client'
import { renderApp } from '../../test/renderApp'
import { ADMIN, EMPLOYEE, apiError, json, mockApi, signedInAs, signedOut, tokenFor } from '../../test/mockApi'

const emptyUsers = () => json(200, { items: [], page: 1, page_size: 25, total: 0 })

describe('TC-AUTH-01 login (FR-AUTH-01)', () => {
  it('signs in with valid credentials and returns to the requested page', async () => {
    const server = mockApi({
      ...signedOut,
      'POST /api/v1/auth/login': () => json(200, tokenFor(ADMIN)),
      'GET /api/v1/users': emptyUsers,
    })
    renderApp('/users')

    const user = userEvent.setup()
    await user.type(await screen.findByLabelText('Email'), 'admin@example.com')
    await user.type(screen.getByLabelText('Password'), 'Correct-Horse-9')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { name: 'Users' })).toBeInTheDocument()
    expect(server.callsTo('POST', '/api/v1/auth/login')[0].body).toEqual({
      email: 'admin@example.com',
      password: 'Correct-Horse-9',
    })
    // The users request carries the access token from the login response.
    await waitFor(() =>
      expect(server.callsTo('GET', '/api/v1/users')[0]?.authorization).toBe(`Bearer token-${ADMIN.id}`),
    )
  })

  it('shows an error for invalid credentials', async () => {
    mockApi({
      ...signedOut,
      'POST /api/v1/auth/login': () => apiError(401, 'unauthorized', 'Invalid email or password.'),
    })
    renderApp('/login')

    const user = userEvent.setup()
    await user.type(await screen.findByLabelText('Email'), 'admin@example.com')
    await user.type(screen.getByLabelText('Password'), 'wrong')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password.')
  })

  it('requires email and password before submitting', async () => {
    const server = mockApi({ ...signedOut })
    renderApp('/login')

    await userEvent.click(await screen.findByRole('button', { name: 'Sign in' }))

    expect(await screen.findAllByText('This field is required.')).toHaveLength(2)
    expect(server.callsTo('POST', '/api/v1/auth/login')).toHaveLength(0)
  })
})

describe('TC-AUTH-02 protected pages (FR-AUTH-02)', () => {
  it('sends anonymous visitors to the login page', async () => {
    mockApi({ ...signedOut })
    renderApp('/users')

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('restores the session from the refresh cookie on page load', async () => {
    mockApi({ ...signedInAs(ADMIN) })
    renderApp('/')

    expect(await screen.findByRole('heading', { name: 'Welcome, Ada Admin' })).toBeInTheDocument()
  })

  it('refreshes an expired access token once and replays the request', async () => {
    let refreshes = 0
    const server = mockApi({
      'POST /api/v1/auth/refresh': () => {
        refreshes += 1
        return json(200, tokenFor(ADMIN, `fresh-${refreshes}`))
      },
      'GET /api/v1/roles': (request) =>
        request.headers.get('Authorization') === 'Bearer fresh-1'
          ? json(200, [])
          : apiError(401, 'unauthorized', 'Invalid or expired access token.'),
    })

    const result = await api.GET('/api/v1/roles')

    expect(result.response.status).toBe(200)
    expect(refreshes).toBe(1)
    expect(server.callsTo('GET', '/api/v1/roles').map((c) => c.authorization)).toEqual([
      null,
      'Bearer fresh-1',
    ])
  })
})

describe('TC-AUTH-03 role-based UI (FR-AUTH-03)', () => {
  it('shows the Users menu to administrators', async () => {
    mockApi({ ...signedInAs(ADMIN) })
    renderApp('/')

    const nav = await screen.findByRole('menu', { name: 'main navigation' })
    expect(within(nav).getByText('Users')).toBeInTheDocument()
  })

  it('hides the Users menu and blocks the page for employees', async () => {
    mockApi({ ...signedInAs(EMPLOYEE) })
    renderApp('/users')

    expect(await screen.findByText('You do not have permission to view this page.')).toBeInTheDocument()
    const nav = screen.getByRole('menu', { name: 'main navigation' })
    expect(within(nav).queryByText('Users')).not.toBeInTheDocument()
  })
})

describe('TC-AUTH-04 logout (FR-AUTH-04)', () => {
  it('ends the session on the server and returns to the login page', async () => {
    const server = mockApi({ ...signedInAs(ADMIN) })
    renderApp('/')

    await userEvent.click(await screen.findByRole('button', { name: 'Log out' }))

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    expect(server.callsTo('POST', '/api/v1/auth/logout')).toHaveLength(1)
  })
})

describe('Arabic and right-to-left layout', () => {
  it('switches the interface to Arabic and RTL', async () => {
    mockApi({ ...signedOut })
    renderApp('/login')

    await userEvent.click(await screen.findByText('العربية'))

    expect(await screen.findByRole('button', { name: 'دخول' })).toBeInTheDocument()
    expect(document.documentElement.dir).toBe('rtl')
    expect(document.documentElement.lang).toBe('ar')
  })
})
