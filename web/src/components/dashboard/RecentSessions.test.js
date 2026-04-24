import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import RecentSessions from './RecentSessions.vue'

const push = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push,
  }),
}))

const sessions = [
  {
    project_id: 'provider-history',
    session_id: 'session-1',
    preview: 'recent session',
    project_path: '/tmp/provider-history',
    message_count: 3,
    timestamp: 1713096000,
  },
]

describe('RecentSessions', () => {
  beforeEach(() => {
    push.mockReset()
  })

  it('keeps recent session navigation under the selected source', async () => {
    const wrapper = mount(RecentSessions, {
      props: {
        sessions,
        source: 'codex',
      },
      global: {
        stubs: {
          'router-link': {
            props: ['to'],
            template: '<a :href="to"><slot /></a>',
          },
        },
      },
    })

    expect(wrapper.get('a').attributes('href')).toBe('/sources/codex/projects')

    await wrapper.get('button').trigger('click')

    expect(push).toHaveBeenCalledWith('/sources/codex/projects/provider-history/sessions/session-1')
  })
})
