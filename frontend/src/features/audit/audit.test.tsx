import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { renderApp } from '../../test/renderApp'
import { ADMIN, EMPLOYEE, json, mockApi, signedInAs } from '../../test/mockApi'
import type { AuditLog } from './api'

const JANE_ID = '33333333-3333-3333-3333-333333333333'

const entry = (overrides: Partial<AuditLog>): AuditLog => ({
  id: crypto.randomUUID(),
  occurred_at: '2026-10-22T09:30:00Z',
  actor_type: 'user',
  actor: { id: ADMIN.id, full_name: ADMIN.full_name, email: ADMIN.email },
  action: 'user.updated',
  target_type: 'user',
  target_id: JANE_ID,
  target_label: 'Jane Doe',
  changes: null,
  request_id: 'req-1',
  ip_address: '10.0.0.7',
  ...overrides,
})

const EDITED = entry({
  changes: { full_name: ['Jane Roe', 'Jane Doe'], roles: [['employee'], ['legal']] },
  request_id: 'req-edit-jane',
})
const FAILED = entry({ actor_type: 'anonymous', actor: null, action: 'auth.login_failed' })
const BY_SYSTEM = entry({ actor_type: 'system', actor: null, action: 'user.created', target_label: 'Root' })

const page = (items: AuditLog[]) => json(200, { items, page: 1, page_size: 25, total: items.length })

describe('TC-AUD-02 audit log page (FR-AUD-02)', () => {
  it('shows who did what to which record, and when', async () => {
    mockApi({ ...signedInAs(ADMIN), 'GET /api/v1/audit-logs': () => page([EDITED, FAILED, BY_SYSTEM]) })
    renderApp('/audit-log')

    expect(await screen.findByRole('heading', { name: 'Audit log' })).toBeInTheDocument()
    const edited = (await screen.findByText('Edited user')).closest('tr')!
    expect(within(edited).getByText(ADMIN.full_name)).toBeInTheDocument()
    expect(within(edited).getByRole('link', { name: 'Jane Doe' })).toHaveAttribute(
      'href',
      `/users/${JANE_ID}`,
    )
    expect(within(edited).getByText(/Oct 22, 2026/)).toBeInTheDocument()

    expect(screen.getByText('Failed sign-in')).toBeInTheDocument()
    expect(screen.getByText('Not signed in')).toBeInTheDocument()
    expect(screen.getByText('System')).toBeInTheDocument()
  })

  it('expands a record to show what changed', async () => {
    mockApi({ ...signedInAs(ADMIN), 'GET /api/v1/audit-logs': () => page([EDITED]) })
    renderApp('/audit-log')

    const user = userEvent.setup()
    await user.click((await screen.findAllByRole('button', { name: /expand row/i }))[0])

    const before = await screen.findByText('Jane Roe')
    const changes = within(before.closest('table')!)
    expect(changes.getByText('Full name')).toBeInTheDocument()
    expect(changes.getByText('Employee')).toBeInTheDocument() // role codes shown as role names
    expect(changes.getByText('Legal User')).toBeInTheDocument()
    expect(screen.getByText('req-edit-jane')).toBeInTheDocument()
    expect(screen.getByText('10.0.0.7')).toBeInTheDocument()
  })

  it('sends search and action filters to the server', async () => {
    const server = mockApi({ ...signedInAs(ADMIN), 'GET /api/v1/audit-logs': () => page([EDITED]) })
    renderApp('/audit-log')

    const user = userEvent.setup()
    await user.type(await screen.findByLabelText('Search by person or record'), 'jane')
    await waitFor(() =>
      expect(server.callsTo('GET', '/api/v1/audit-logs').some((c) => c.search.includes('q=jane'))).toBe(true),
    )

    await user.click(screen.getByLabelText('Filter by action'))
    await user.click(await screen.findByTitle('Failed sign-in'))
    await waitFor(() => {
      const last = server.callsTo('GET', '/api/v1/audit-logs').at(-1)!
      expect(last.search).toContain('action=auth.login_failed')
      expect(last.search).toContain('q=jane')
      expect(last.search).toContain('page=1')
    })
  })
})

describe('TC-AUD-03 audit records are read-only (FR-AUD-03)', () => {
  it('offers no way to edit or delete a record', async () => {
    mockApi({ ...signedInAs(ADMIN), 'GET /api/v1/audit-logs': () => page([EDITED, FAILED]) })
    renderApp('/audit-log')

    expect(await screen.findByText('Edited user')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /edit|delete|remove/i })).not.toBeInTheDocument()
    expect(screen.getByText(/Audit records are read-only/)).toBeInTheDocument()
  })

  it('is closed to users without the audit permission', async () => {
    const server = mockApi({ ...signedInAs(EMPLOYEE) })
    renderApp('/audit-log')

    expect(await screen.findByText('You do not have permission to view this page.')).toBeInTheDocument()
    expect(server.callsTo('GET', '/api/v1/audit-logs')).toHaveLength(0)
  })
})
