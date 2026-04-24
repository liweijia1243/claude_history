import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { reactive } from 'vue'

import App from './App.vue'

const push = vi.fn()
const replace = vi.fn()
const route = reactive({
  path: '/',
  query: {},
  params: {},
})

vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => ({
    push,
    replace,
  }),
}))

vi.mock('./composables/useTheme', () => ({
  useTheme: () => ({
    isDark: false,
    toggleTheme: vi.fn(),
    initTheme: vi.fn(),
  }),
}))

function mountApp() {
  return mount(App, {
    global: {
      stubs: {
        'router-view': { template: '<div />' },
      },
    },
  })
}

describe('App source switcher', () => {
  beforeEach(() => {
    const storage = new Map()
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(key => storage.get(key) || null),
      setItem: vi.fn((key, value) => storage.set(key, String(value))),
      removeItem: vi.fn(key => storage.delete(key)),
      clear: vi.fn(() => storage.clear()),
    })
    push.mockReset()
    replace.mockReset()
    route.path = '/'
    route.query = {}
    route.params = {}
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('keeps fallback source options when fetching sources fails', async () => {
    global.fetch = vi.fn(() => Promise.reject(new Error('offline')))

    const wrapper = mountApp()
    await flushPromises()

    expect(global.fetch).toHaveBeenCalledWith('/api/sources')
    expect(wrapper.findAll('option').map(option => option.attributes('value'))).toEqual([
      'claude',
      'codex',
    ])
  })

  it('replaces fallback source options with API data when fetching sources succeeds', async () => {
    global.fetch = vi.fn(() => Promise.resolve({
      json: () => Promise.resolve([
        { id: 'codex', name: 'Codex Local', available: true },
      ]),
    }))

    const wrapper = mountApp()
    await flushPromises()

    const options = wrapper.findAll('option')
    expect(options.map(option => option.attributes('value'))).toEqual(['codex'])
    expect(options[0].text()).toBe('Codex Local')
  })
})
