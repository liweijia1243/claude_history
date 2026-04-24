import { mount, flushPromises } from '@vue/test-utils'
import { nextTick, reactive } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import Dashboard from './Dashboard.vue'

const route = reactive({
  path: '/',
  params: {},
})

vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => ({
    push: vi.fn(),
  }),
}))

function deferred() {
  let resolve
  const promise = new Promise(resolvePromise => {
    resolve = resolvePromise
  })
  return { promise, resolve }
}

function statsResponse(totalCommands) {
  return {
    summary: {
      total_commands: totalCommands,
      total_sessions: 0,
      total_projects: 0,
      total_tokens: { input: 0, output: 0 },
    },
    changes: {
      commands_pct: 0,
      sessions_pct: 0,
      projects_new: 0,
      tokens_pct: 0,
    },
    daily_series: [],
    message_types: [],
    top_projects: [],
    hourly_distribution: [],
    session_durations: [],
  }
}

function mountDashboard() {
  return mount(Dashboard, {
    global: {
      stubs: {
        StatCard: {
          props: ['label', 'value'],
          template: '<div data-stat-card>{{ label }}:{{ value }}</div>',
        },
        TrendChart: true,
        MessageTypeChart: true,
        TopProjectsChart: true,
        HourlyChart: true,
        TokenUsageChart: true,
        SessionDurationChart: true,
        RecentSessions: true,
      },
    },
  })
}

describe('Dashboard', () => {
  beforeEach(() => {
    route.path = '/'
    route.params = {}
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('ignores stale dashboard responses after source changes', async () => {
    const claudeStats = deferred()
    const claudeRecent = deferred()
    const codexStats = deferred()
    const codexRecent = deferred()

    global.fetch = vi.fn(url => {
      if (url === '/api/claude/dashboard-stats?range=30d') return claudeStats.promise
      if (url === '/api/claude/recent-sessions?limit=4') return claudeRecent.promise
      if (url === '/api/codex/dashboard-stats?range=30d') return codexStats.promise
      if (url === '/api/codex/recent-sessions?limit=4') return codexRecent.promise
      return Promise.reject(new Error(`Unexpected URL: ${url}`))
    })

    const wrapper = mountDashboard()
    await nextTick()

    route.path = '/sources/codex'
    route.params = { source: 'codex' }
    await nextTick()

    codexStats.resolve({ ok: true, json: () => Promise.resolve(statsResponse(9)) })
    codexRecent.resolve({ ok: true, json: () => Promise.resolve([]) })
    await flushPromises()

    expect(wrapper.text()).toContain('总命令数:9')

    claudeStats.resolve({ ok: true, json: () => Promise.resolve(statsResponse(1)) })
    claudeRecent.resolve({ ok: true, json: () => Promise.resolve([]) })
    await flushPromises()

    expect(wrapper.text()).toContain('总命令数:9')
    expect(wrapper.text()).not.toContain('总命令数:1')
  })
})
