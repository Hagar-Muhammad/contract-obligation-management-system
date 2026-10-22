import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'
import { setSession } from '../api/client'
import i18n from '../i18n'

beforeEach(async () => {
  await i18n.changeLanguage('en')
})

afterEach(() => {
  cleanup()
  setSession(null)
  vi.unstubAllGlobals()
})

// jsdom does not implement matchMedia, which Ant Design's responsive helpers use.
if (!window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as MediaQueryList
}

// Ant Design measures elements; jsdom has no layout, so give it a no-op ResizeObserver.
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as unknown as typeof ResizeObserver

// jsdom does not support getComputedStyle(element, pseudoElement); Ant Design only needs the element form.
const { getComputedStyle } = window
window.getComputedStyle = (element: Element) => getComputedStyle(element)
