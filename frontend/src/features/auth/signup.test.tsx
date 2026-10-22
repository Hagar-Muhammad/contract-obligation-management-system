import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { renderApp } from '../../test/renderApp'
import { EMPLOYEE, apiError, json, mockApi, signedOut, tokenFor } from '../../test/mockApi'

const signupEnabled = { 'GET /api/v1/auth/options': () => json(200, { self_signup_enabled: true }) }

async function fillSignUp(confirm = 'Fresh-Pass-123') {
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('Full name'), 'Eve Employee')
  await user.type(screen.getByLabelText('Work email'), 'eve@example.com')
  await user.type(screen.getByLabelText('Password'), 'Fresh-Pass-123')
  await user.type(screen.getByLabelText('Confirm password'), confirm)
  await user.click(screen.getByRole('button', { name: 'Create account' }))
}

describe('TC-CR-01 self sign-up (CR-01)', () => {
  it('links from the login page to sign-up when it is enabled', async () => {
    mockApi({ ...signedOut, ...signupEnabled })
    renderApp('/login')

    await userEvent.click(await screen.findByRole('link', { name: 'Create an account' }))

    expect(await screen.findByRole('heading', { name: 'Create your account' })).toBeInTheDocument()
  })

  it('hides the sign-up link when sign-up is disabled', async () => {
    mockApi({ ...signedOut, 'GET /api/v1/auth/options': () => json(200, { self_signup_enabled: false }) })
    renderApp('/login')

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    await waitFor(() =>
      expect(screen.queryByRole('link', { name: 'Create an account' })).not.toBeInTheDocument(),
    )
  })

  it('creates the account, signs the user in and opens the home page', async () => {
    const server = mockApi({
      ...signedOut,
      ...signupEnabled,
      'POST /api/v1/auth/register': () => json(201, tokenFor(EMPLOYEE)),
    })
    renderApp('/signup')

    await fillSignUp()

    expect(await screen.findByRole('heading', { name: 'Welcome, Eve Employee' })).toBeInTheDocument()
    // The confirmation field stays in the browser; the role is never sent.
    expect(server.callsTo('POST', '/api/v1/auth/register')[0].body).toEqual({
      full_name: 'Eve Employee',
      email: 'eve@example.com',
      password: 'Fresh-Pass-123',
      preferred_language: 'en',
    })
  })

  it('checks that both passwords match before sending', async () => {
    const server = mockApi({ ...signedOut, ...signupEnabled })
    renderApp('/signup')

    await fillSignUp('Different-Pass-1')

    expect(await screen.findByText('The passwords do not match.')).toBeInTheDocument()
    expect(server.callsTo('POST', '/api/v1/auth/register')).toHaveLength(0)
  })

  it('tells the visitor when the email is already registered', async () => {
    mockApi({
      ...signedOut,
      ...signupEnabled,
      'POST /api/v1/auth/register': () =>
        apiError(409, 'conflict', 'A user with this e-mail already exists.'),
    })
    renderApp('/signup')

    await fillSignUp()

    expect(await screen.findByText('This email is already registered. Sign in instead.')).toBeInTheDocument()
  })

  it('explains when sign-up has been switched off', async () => {
    mockApi({
      ...signedOut,
      ...signupEnabled,
      'POST /api/v1/auth/register': () => apiError(403, 'forbidden', 'Self sign-up is disabled.'),
    })
    renderApp('/signup')

    await fillSignUp()

    expect(await screen.findByRole('alert')).toHaveTextContent('Sign-up is turned off.')
  })
})
