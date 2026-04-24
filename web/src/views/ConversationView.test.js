import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import ConversationView from './ConversationView.vue'

const push = vi.fn()
const route = {
  path: '/sources/codex/projects/project-1/sessions/session-1',
  query: {},
  params: { source: 'codex' },
}

vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => ({
    push,
  }),
}))

function mountConversation() {
  return mount(ConversationView, {
    props: {
      projectId: 'project-1',
      sessionId: 'session-1',
    },
    global: {
      stubs: {
        ToolCallBlock: true,
        ThinkingBlock: true,
        CodeBlock: true,
        Transition: false,
      },
    },
  })
}

describe('ConversationView', () => {
  beforeEach(() => {
    const storage = new Map()
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(key => storage.get(key) || null),
      setItem: vi.fn((key, value) => storage.set(key, String(value))),
    })
    push.mockReset()
    route.query = {}
    route.params = { source: 'codex' }
    global.fetch = vi.fn(() => Promise.resolve({
      ok: false,
      json: () => Promise.resolve({ detail: 'Session not found' }),
    }))
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('navigates back to source projects when a conversation fetch is not OK', async () => {
    mountConversation()
    await flushPromises()

    expect(global.fetch).toHaveBeenCalledWith('/api/codex/projects/project-1/sessions/session-1')
    expect(push).toHaveBeenCalledWith('/sources/codex/projects')
  })
})
