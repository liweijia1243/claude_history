import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import HistorySearch from './HistorySearch.vue'

const replace = vi.fn()
const push = vi.fn()
const route = {
  query: {},
}

vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => ({
    replace,
    push,
  }),
}))

function createFetchMock() {
  return vi.fn(() => Promise.resolve({
    ok: true,
    json: () => Promise.resolve({
      items: [
        {
          timestamp: 1713096000000,
          display: 'open provider history',
          project: '/tmp/provider-history',
          project_id: 'provider-history',
          sessionId: 'session-1',
        },
      ],
      total: 1,
      pages: 1,
    }),
  }))
}

describe('HistorySearch', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    route.query = {}
    replace.mockReset()
    push.mockReset()
    global.fetch = createFetchMock()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('fetches history from the selected source', async () => {
    mount(HistorySearch, {
      props: {
        source: 'codex',
        syncUrl: true,
        initiallyActive: true,
      },
    })

    await flushPromises()

    expect(global.fetch).toHaveBeenCalledWith('/api/codex/history?page=1&limit=50')
  })

  it('refetches with the new project filter when projectPath changes', async () => {
    const wrapper = mount(HistorySearch, {
      props: {
        source: 'codex',
        projectPath: '/repo/alpha',
        syncUrl: false,
        initiallyActive: true,
      },
    })
    await flushPromises()

    await wrapper.setProps({ projectPath: '/repo/beta' })
    await flushPromises()

    expect(global.fetch).toHaveBeenLastCalledWith('/api/codex/history?page=1&limit=50&project=%2Frepo%2Fbeta')
  })

  it('syncs search query to the selected source route', async () => {
    const wrapper = mount(HistorySearch, {
      props: {
        source: 'codex',
        syncUrl: true,
        initiallyActive: true,
      },
    })
    await flushPromises()

    await wrapper.get('input').setValue('tokens')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()

    expect(replace).toHaveBeenCalledWith({
      path: '/sources/codex/history',
      query: { q: 'tokens' },
    })
    expect(global.fetch).toHaveBeenLastCalledWith('/api/codex/history?page=1&limit=50&search=tokens')
  })

  it('opens conversations under the selected source route', async () => {
    const wrapper = mount(HistorySearch, {
      props: {
        source: 'codex',
        syncUrl: false,
        initiallyActive: true,
      },
    })
    await flushPromises()

    await wrapper.find('[data-history-item]').trigger('dblclick')

    expect(push).toHaveBeenCalledWith({
      path: '/sources/codex/projects/provider-history/sessions/session-1',
      query: {
        msgTimestamp: '1713096000000',
        source: 'history',
      },
    })
  })
})
