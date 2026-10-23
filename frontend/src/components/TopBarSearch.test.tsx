import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { renderApp } from '../test/renderApp'
import { ADMIN, json, mockApi, signedInAs } from '../test/mockApi'

const RESULTS = {
  contracts: [{ id: 'c1', contract_number: 'CT-2026-0142', title: 'Westgate lease' }],
  parties: [{ id: 'p1', display_name: 'Westgate Holdings', party_type: 'organization' }],
  properties: [{ id: 'pr1', code: 'WG-1', name: 'Westgate Mall' }],
  obligations: [
    {
      id: 'o1',
      title: 'Westgate rent',
      contract_number: 'CT-2026-0142',
      due_date: '2030-01-01',
      effective_status: 'pending',
    },
  ],
}
const empty = () => json(200, { items: [], page: 1, page_size: 25, total: 0 })

describe('TC-SEARCH-01 top-bar search (FR-SEARCH-01)', () => {
  it('shows what matches in each kind of record and opens the full contract search', async () => {
    const server = mockApi({
      ...signedInAs(ADMIN),
      'GET /api/v1/search': () => json(200, RESULTS),
      'GET /api/v1/contracts': empty,
      'GET /api/v1/contracts/counts': () =>
        json(200, { active: 0, draft: 0, expiring: 0, ended: 0, archived: 0 }),
      'GET /api/v1/contracts/defaults': () =>
        json(200, { next_number: 'CT-2026-0001', default_currency: 'EGP', expiring_soon_days: 60 }),
      'GET /api/v1/contract-types': () => json(200, []),
      'GET /api/v1/contract-statuses': () => json(200, []),
      'GET /api/v1/parties': empty,
      'GET /api/v1/properties': empty,
    })
    renderApp('/')

    const user = userEvent.setup()
    await user.type(await screen.findByLabelText('Search contracts, parties, properties…'), 'westgate')

    expect(await screen.findByText('Westgate lease')).toBeInTheDocument()
    expect(screen.getByText('Westgate rent')).toBeInTheDocument()
    expect(screen.getByText('Westgate Holdings')).toBeInTheDocument()
    expect(screen.getByText('Westgate Mall')).toBeInTheDocument()
    expect(server.callsTo('GET', '/api/v1/search').at(-1)!.search).toContain('q=westgate')

    await user.click(screen.getByText('Search all contracts for “westgate”'))
    expect(await screen.findByRole('heading', { name: 'Contracts' })).toBeInTheDocument()
    await waitFor(() =>
      expect(server.callsTo('GET', '/api/v1/contracts').some((c) => c.search.includes('q=westgate'))).toBe(
        true,
      ),
    )
    expect(screen.getByLabelText('Number, title, party or property')).toHaveValue('westgate')
  })

  it('waits for at least two characters', async () => {
    const server = mockApi({ ...signedInAs(ADMIN), 'GET /api/v1/search': () => json(200, RESULTS) })
    renderApp('/')

    const user = userEvent.setup()
    await user.type(await screen.findByLabelText('Search contracts, parties, properties…'), 'w')
    await new Promise((resolve) => setTimeout(resolve, 400))
    expect(server.callsTo('GET', '/api/v1/search')).toHaveLength(0)
  })
})
