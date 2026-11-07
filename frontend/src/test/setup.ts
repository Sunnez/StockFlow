import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'

Object.defineProperty(HTMLDialogElement.prototype, 'showModal', {
  configurable: true,
  value(this: HTMLDialogElement) {
    this.open = true
  },
})
Object.defineProperty(HTMLDialogElement.prototype, 'close', {
  configurable: true,
  value(this: HTMLDialogElement) {
    this.open = false
  },
})

beforeEach(() => {
  // Fail every unhandled request. Tests must never reach the real FastAPI server.
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.reject(new Error('Unhandled test request'))),
  )
  vi.stubGlobal('BroadcastChannel', undefined)
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })),
  )
  localStorage.clear()
  document.cookie = 'csrf_token=; Max-Age=0; Path=/'
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})
