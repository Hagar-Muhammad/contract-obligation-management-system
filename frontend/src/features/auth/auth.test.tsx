import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { api } from '../../api/client'
import { renderApp } from '../../test/renderApp'
import { ADMIN, EMPLOYEE, apiError, json, mockApi, signedInAs, signedOut, tokenFor } from '../../test/mockApi'

const emptyUsers = () => json(200, { items: [], page: 1, page_size: 25, total: 0 })
const noRoles = () => json(200, [])

async function signIn(email: string, password: string, { remember = false } = {}) {
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('Work email'), email)
  await user.type(screen.getByLabelText('Password'), password)
  if (remember) await user.click(screen.getByLabelText('Keep me signed in on this device'))
  await user.click(screen.getByRole('button', { name: 'Sign in' }))
}

describe('TC-AUTH-01 login (FR-AUTH-01)', () => {
  it('signs in with valid credentials and returns to the requested page', async () => {
    const server = mockApi({
      ...signedOut,
      'POST /api/v1/auth/login': () => json(200, tokenFor(ADMIN)),
      'GET /api/v1/users': emptyUsers,
      'GET /api/v1/roles': noRoles,
    })
    renderApp('/users')

    await signIn('admin@example.com', 'Correct-Horse-9', { remember: true })

    expect(await screen.findByRole('heading', { name: 'Users & roles' })).toBeInTheDocument()
    expect(server.callsTo('POST', '/api/v1/auth/login')[0].body).toEqual({
      email: 'admin@example.com',
      password: 'Correct-Horse-9',
      remember_me: true,
    })
    // The users request carries the access token from the login response.
    await waitFor(() =>
      expect(server.callsTo('GET', '/api/v1/users')[0]?.authorization).toBe(`Bearer token-${ADMIN.id}`),
    )
  })

  it('does not keep the session unless asked to', async () => {
    const server = mockApi({ ...signedOut, 'POST /api/v1/auth/login': () => json(200, tokenFor(ADMIN)) })
    renderApp('/login')

    await signIn('admin@example.com', 'Correct-Horse-9')

    await waitFor(() => expect(server.callsTo('POST', '/api/v1/auth/login')).toHaveLength(1))
    expect(server.callsTo('POST', '/api/v1/auth/login')[0].body).toMatchObject({ remember_me: false })
  })

  it('shows an error for invalid credentials', async () => {
    mockApi({
      ...signedOut,
      'POST /api/v1/auth/login': () => apiError(401, 'unauthorized', 'Invalid email or password.'),
    })
    renderApp('/login')

    await signIn('admin@example.com', 'wrong')

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password.')
  })

  it('requires email and password before submitting', async () => {
    const server = mockApi({ ...signedOut })
    renderApp('/login')

    await userEvent.click(await screen.findByRole('button', { name: 'Sign in' }))

    expect(await screen.findAllByText('This field is required.')).toHaveLength(2)
    expect(server.callsTo('POST', '/api/v1/auth/login')).toHaveLength(0)
  })

  it('explains how to get a new password', async () => {
    mockApi({ ...signedOut })
    renderApp('/login')

    await userEvent.click(await screen.findByRole('button', { name: 'Forgot password?' }))

    expect(
      await screen.findByText(/ask your ConTrack administrator to set a new password/),
    ).toBeInTheDocument()
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

    expect(await screen.findByRole('heading', { name: /Ada/ })).toBeInTheDocument()
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
  it('shows every section an administrator can use', async () => {
    mockApi({ ...signedInAs(ADMIN) })
    renderApp('/')

    const nav = await screen.findByRole('navigation', { name: 'Main navigation' })
    for (const label of ['Dashboard', 'Contracts', 'Obligations', 'Reports', 'Audit log', 'Users & roles']) {
      expect(within(nav).getByRole('link', { name: label })).toBeInTheDocument()
    }
  })

  it('hides admin pages from employees and blocks them by URL', async () => {
    mockApi({ ...signedInAs(EMPLOYEE) })
    renderApp('/users')

    expect(await screen.findByText('You do not have permission to view this page.')).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Main navigation' })
    expect(within(nav).queryByRole('link', { name: 'Users & roles' })).not.toBeInTheDocument()
    expect(within(nav).queryByRole('link', { name: 'Audit log' })).not.toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: 'Obligations' })).toBeInTheDocument()
  })

  it('shows the user and their role in the top bar', async () => {
    mockApi({ ...signedInAs(EMPLOYEE) })
    renderApp('/')

    const account = await screen.findByRole('button', { name: 'Account' })
    expect(within(account).getByText('Eve Employee')).toBeInTheDocument()
    expect(within(account).getByText('Employee')).toBeInTheDocument()
  })

  it('marks pages that later modules deliver', async () => {
    mockApi({ ...signedInAs(ADMIN) })
    renderApp('/obligations')

    expect(await screen.findByText('Obligations is on its way')).toBeInTheDocument()
    expect(screen.getByText('This page arrives with module 6 of the delivery plan.')).toBeInTheDocument()
  })
})

describe('TC-AUTH-04 logout (FR-AUTH-04)', () => {
  it('ends the session on the server and returns to the login page', async () => {
    const server = mockApi({ ...signedInAs(ADMIN) })
    renderApp('/')

    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: 'Account' }))
    await user.click(await screen.findByText('Log out'))

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    expect(server.callsTo('POST', '/api/v1/auth/logout')).toHaveLength(1)
  })
})

describe('Arabic and right-to-left layout', () => {
  it('switches the sign-in page to Arabic and RTL', async () => {
    mockApi({ ...signedOut })
    renderApp('/login')

    await userEvent.click(await screen.findByText('العربية'))

    expect(await screen.findByRole('button', { name: 'دخول' })).toBeInTheDocument()
    expect(document.documentElement.dir).toBe('rtl')
    expect(document.documentElement.lang).toBe('ar')
  })

  it('switches language from the top bar when signed in', async () => {
    mockApi({ ...signedInAs(ADMIN) })
    renderApp('/')

    await userEvent.click(await screen.findByRole('button', { name: 'Language' }))

    expect(await screen.findByRole('link', { name: 'لوحة التحكم' })).toBeInTheDocument()
    expect(document.documentElement.dir).toBe('rtl')
  })
})
