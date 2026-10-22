import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'
import App from './App'
import i18n from './i18n'

describe('App shell', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it('renders the application title in English by default', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: 'Contract & Obligation Management' })).toBeInTheDocument()
    expect(document.documentElement.dir).toBe('ltr')
  })

  it('switches to Arabic with right-to-left layout', async () => {
    render(<App />)
    await userEvent.click(screen.getByText('العربية'))
    expect(await screen.findByRole('heading', { name: 'إدارة العقود والالتزامات' })).toBeInTheDocument()
    expect(document.documentElement.dir).toBe('rtl')
    expect(document.documentElement.lang).toBe('ar')
  })
})
