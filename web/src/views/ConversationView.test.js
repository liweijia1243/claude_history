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

function mountConversation(stubs = {}) {
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
        ...stubs,
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

  it('groups Codex spawn_agent calls with agent tools instead of regular tools', async () => {
    localStorage.setItem('conv_showAgents', 'true')
    localStorage.setItem('conv_showTools', 'false')
    global.fetch = vi.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        conversation: [
          {
            role: 'assistant',
            content: '',
            thinking: '',
            tool_uses: [
              {
                id: 'spawn-1',
                name: 'spawn_agent',
                input: { agent_type: 'worker', message: 'do work' },
                metadata: { agent_id: 'child-thread' },
              },
            ],
            tool_results: [],
            model: 'gpt-5.5',
            timestamp: '2026-04-24T10:00:00Z',
          },
        ],
        subagents: [
          {
            filename: 'child-thread',
            type: 'worker',
            description: 'do work',
          },
        ],
        metadata: {},
        total_raw_messages: 1,
      }),
    }))

    const wrapper = mountConversation({
      ToolCallBlock: {
        name: 'ToolCallBlock',
        props: ['toolUses'],
        template: '<div class="tool-block">{{ toolUses.map(t => t.name).join(",") }}</div>',
      },
    })
    await flushPromises()

    const blocks = wrapper.findAll('.tool-block')
    expect(blocks).toHaveLength(1)
    expect(blocks[0].text()).toBe('spawn_agent')
  })
})
