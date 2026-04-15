# Plans 页面管理重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Plans 页面从顶部横向 tab 重构为三栏文档管理视图，支持标题/文件名/摘要搜索、排序、时间筛选和右侧 Markdown 预览。

**Architecture:** 保持后端 `/api/plans` 与 `/api/plans/{name}` 不变，在前端读取 plan 列表后拉取 Markdown 内容并派生 `displayTitle`、`summary`、`searchText` 等字段。页面逻辑拆成“纯函数工具 + PlansView 视图状态”两层：纯函数负责标题摘要提取、筛选排序与选中项决策，`PlansView.vue` 负责数据加载、交互状态和三栏布局渲染。

**Tech Stack:** Vue 3、Vite、marked、highlight.js、Vitest、@vue/test-utils、jsdom

---

## File Structure

- Modify: `web/package.json`
  - 添加 `test` / `test:run` 脚本与测试依赖声明。
- Modify: `web/package-lock.json`
  - 记录新增的 Vitest、@vue/test-utils、jsdom 依赖。
- Modify: `web/vite.config.js`
  - 添加 Vitest `test` 配置，使用 `jsdom` 环境运行 Vue 组件测试。
- Create: `web/src/utils/planMetadata.js`
  - 纯函数：提取 Markdown 标题、生成摘要、构建搜索文本、过滤排序列表、计算筛选结果变化后的选中项。
- Create: `web/src/utils/planMetadata.test.js`
  - 为纯函数写单元测试，锁定搜索/排序/摘要/选中逻辑。
- Create: `web/src/views/PlansView.test.js`
  - 使用 fetch mock 验证 Plans 页面加载、筛选、自动切换选中项与空状态。
- Modify: `web/src/views/PlansView.vue`
  - 实现三栏布局、数据加载、筛选状态、卡片列表和右侧预览。

### Task 1: 配置 Plans 页测试基础设施

**Files:**
- Modify: `web/package.json`
- Modify: `web/package-lock.json`
- Modify: `web/vite.config.js`

- [ ] **Step 1: 先确认当前没有前端测试脚本**

Run: `cd /home/weijiali/phi_ws/vibe_coding/claude_history/web && npm run test:run`
Expected: FAIL，输出包含类似 `Missing script: "test:run"`

- [ ] **Step 2: 安装 Vitest、Vue Test Utils 和 jsdom**

Run: `cd /home/weijiali/phi_ws/vibe_coding/claude_history/web && npm install -D vitest @vue/test-utils jsdom`
Expected: PASS，输出包含 `added`，并更新 `package-lock.json`

- [ ] **Step 3: 在 `web/package.json` 中添加测试脚本**

```json
{
  "name": "claude-history-viewer",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:run": "vitest run"
  },
  "dependencies": {
    "echarts": "^6.0.0",
    "highlight.js": "^11.11.0",
    "marked": "^15.0.0",
    "vue": "^3.5.0",
    "vue-echarts": "^8.0.1",
    "vue-router": "^4.4.0"
  },
  "devDependencies": {
    "@tailwindcss/typography": "^0.5.19",
    "@tailwindcss/vite": "^4.0.0",
    "@vitejs/plugin-vue": "^5.2.0",
    "@vue/test-utils": "^2.4.6",
    "jsdom": "^26.1.0",
    "tailwindcss": "^4.0.0",
    "vite": "^6.0.0",
    "vitest": "^3.2.4"
  }
}
```

- [ ] **Step 4: 在 `web/vite.config.js` 中启用 jsdom 测试环境**

```js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8787',
    },
  },
  test: {
    environment: 'jsdom',
  },
})
```

- [ ] **Step 5: 运行测试命令确认基础设施可用**

Run: `cd /home/weijiali/phi_ws/vibe_coding/claude_history/web && npm run test:run`
Expected: PASS，输出包含类似 `No test files found` 或 `include: **/*.{test,spec}.?(c|m)[jt]s?(x)`，说明测试命令已可执行

- [ ] **Step 6: 提交测试基础设施改动**

```bash
cd /home/weijiali/phi_ws/vibe_coding/claude_history
git add web/package.json web/package-lock.json web/vite.config.js
git commit -m "chore: 添加 Plans 页面测试基础设施"
```

### Task 2: 为 Plans 元数据派生逻辑写纯函数测试并实现

**Files:**
- Create: `web/src/utils/planMetadata.js`
- Create: `web/src/utils/planMetadata.test.js`

- [ ] **Step 1: 先写失败的纯函数测试**

```js
import { describe, expect, it } from 'vitest'
import {
  extractPlanTitle,
  extractPlanSummary,
  enrichPlan,
  filterAndSortPlans,
  resolveSelectedPlanName,
} from './planMetadata'

describe('planMetadata', () => {
  it('uses markdown h1 as display title and falls back to filename', () => {
    expect(extractPlanTitle('# Weekly sync\n\nbody', 'weekly-sync')).toBe('Weekly sync')
    expect(extractPlanTitle('No heading here', 'fallback-name')).toBe('fallback-name')
  })

  it('builds a summary from body text without the h1 heading', () => {
    expect(
      extractPlanSummary('# Weekly sync\n\nFirst paragraph.\n\nSecond paragraph.', 80)
    ).toBe('First paragraph. Second paragraph.')
  })

  it('enriches a plan with title, summary and searchText', () => {
    expect(
      enrichPlan(
        {
          name: 'weekly-sync',
          filename: 'weekly-sync.md',
          size: 1200,
          modified: 1713000000,
        },
        '# Weekly sync\n\nSummarise current blockers.'
      )
    ).toMatchObject({
      displayTitle: 'Weekly sync',
      summary: 'Summarise current blockers.',
      searchText: 'weekly sync weekly-sync.md summarise current blockers.',
    })
  })

  it('filters by title, filename and summary, then sorts by modified desc by default', () => {
    const plans = [
      {
        name: 'older-plan',
        filename: 'older-plan.md',
        displayTitle: 'Release prep',
        summary: 'Prepare checklist',
        searchText: 'release prep older-plan.md prepare checklist',
        size: 400,
        modified: 10,
      },
      {
        name: 'newer-plan',
        filename: 'newer-plan.md',
        displayTitle: 'Dashboard polish',
        summary: 'Polish charts and layout',
        searchText: 'dashboard polish newer-plan.md polish charts and layout',
        size: 600,
        modified: 20,
      },
    ]

    expect(
      filterAndSortPlans(plans, {
        query: 'chart',
        sortBy: 'modified',
        timeRange: 'all',
        now: 30 * 24 * 60 * 60 * 1000,
      }).map(plan => plan.name)
    ).toEqual(['newer-plan'])
  })

  it('switches selection to the first filtered result when current selection disappears', () => {
    expect(
      resolveSelectedPlanName('missing-plan', [{ name: 'first-plan' }, { name: 'second-plan' }])
    ).toBe('first-plan')
  })
})
```

- [ ] **Step 2: 运行纯函数测试确认失败**

Run: `cd /home/weijiali/phi_ws/vibe_coding/claude_history/web && npm run test:run -- src/utils/planMetadata.test.js`
Expected: FAIL，输出包含类似 `Failed to resolve import "./planMetadata"`

- [ ] **Step 3: 实现纯函数工具**

```js
const DAY_IN_MS = 24 * 60 * 60 * 1000

export function extractPlanTitle(content, fallbackName) {
  const match = content.match(/^#\s+(.+)$/m)
  return match?.[1]?.trim() || fallbackName
}

export function extractPlanSummary(content, maxLength = 160) {
  const summary = content
    .replace(/^#\s+.+$/m, '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[(.*?)\]\((.*?)\)/g, '$1')
    .replace(/[>#*-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

  if (!summary) return 'No summary available.'
  return summary.length > maxLength ? `${summary.slice(0, maxLength).trim()}…` : summary
}

export function enrichPlan(plan, content) {
  const displayTitle = extractPlanTitle(content, plan.name)
  const summary = extractPlanSummary(content)

  return {
    ...plan,
    content,
    displayTitle,
    summary,
    searchText: `${displayTitle} ${plan.filename} ${summary}`.toLowerCase(),
  }
}

function matchesTimeRange(plan, timeRange, now) {
  if (timeRange === 'all') return true
  const age = now - plan.modified * 1000
  if (timeRange === '7d') return age <= 7 * DAY_IN_MS
  if (timeRange === '30d') return age <= 30 * DAY_IN_MS
  return true
}

function comparePlans(a, b, sortBy) {
  if (sortBy === 'name') return a.filename.localeCompare(b.filename)
  if (sortBy === 'size') return b.size - a.size
  return b.modified - a.modified
}

export function filterAndSortPlans(plans, { query, sortBy, timeRange, now = Date.now() }) {
  const normalizedQuery = query.trim().toLowerCase()

  return plans
    .filter(plan => matchesTimeRange(plan, timeRange, now))
    .filter(plan => !normalizedQuery || plan.searchText.includes(normalizedQuery))
    .sort((a, b) => comparePlans(a, b, sortBy))
}

export function resolveSelectedPlanName(currentName, filteredPlans) {
  if (filteredPlans.length === 0) return null
  if (filteredPlans.some(plan => plan.name === currentName)) return currentName
  return filteredPlans[0].name
}
```

- [ ] **Step 4: 再次运行纯函数测试确认通过**

Run: `cd /home/weijiali/phi_ws/vibe_coding/claude_history/web && npm run test:run -- src/utils/planMetadata.test.js`
Expected: PASS，输出包含 `5 passed`

- [ ] **Step 5: 提交纯函数工具与测试**

```bash
cd /home/weijiali/phi_ws/vibe_coding/claude_history
git add web/src/utils/planMetadata.js web/src/utils/planMetadata.test.js
git commit -m "test: 添加 Plans 元数据派生逻辑测试"
```

### Task 3: 先写 PlansView 组件行为测试

**Files:**
- Create: `web/src/views/PlansView.test.js`
- Test: `web/src/utils/planMetadata.js`

- [ ] **Step 1: 写组件行为测试，覆盖加载、筛选和自动切换选中项**

```js
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import PlansView from './PlansView.vue'

function flushPromises() {
  return new Promise(resolve => setTimeout(resolve, 0))
}

describe('PlansView', () => {
  beforeEach(() => {
    global.fetch = vi.fn((url) => {
      if (url === '/api/plans') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([
            { name: 'alpha', filename: 'alpha.md', size: 120, modified: 200 },
            { name: 'beta', filename: 'beta.md', size: 300, modified: 100 },
          ]),
        })
      }

      if (url === '/api/plans/alpha') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            name: 'alpha',
            content: '# Alpha plan\n\nFirst summary block.',
          }),
        })
      }

      if (url === '/api/plans/beta') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            name: 'beta',
            content: '# Beta plan\n\nSecond summary block.',
          }),
        })
      }

      return Promise.reject(new Error(`Unexpected URL: ${url}`))
    })
  })

  it('loads plans, selects the first filtered result and renders markdown preview', async () => {
    const wrapper = mount(PlansView)
    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('Alpha plan')
    expect(wrapper.text()).toContain('First summary block.')
    expect(wrapper.html()).toContain('<h1>Alpha plan</h1>')
  })

  it('filters by search text and switches preview when selected plan is filtered out', async () => {
    const wrapper = mount(PlansView)
    await flushPromises()
    await flushPromises()

    await wrapper.get('input[type="search"]').setValue('beta')
    await flushPromises()

    expect(wrapper.text()).toContain('Beta plan')
    expect(wrapper.text()).not.toContain('Alpha plan First summary block.')
    expect(wrapper.html()).toContain('<h1>Beta plan</h1>')
  })

  it('shows an empty state when no plan matches the filters', async () => {
    const wrapper = mount(PlansView)
    await flushPromises()
    await flushPromises()

    await wrapper.get('input[type="search"]').setValue('missing')
    await flushPromises()

    expect(wrapper.text()).toContain('No plans match the current filters.')
    expect(wrapper.text()).toContain('Select a plan from the list to preview its content.')
  })
})
```

- [ ] **Step 2: 运行组件测试确认失败**

Run: `cd /home/weijiali/phi_ws/vibe_coding/claude_history/web && npm run test:run -- src/views/PlansView.test.js`
Expected: FAIL，输出包含类似 `Unable to find an input element` 或断言失败，因为当前页面还是旧布局

- [ ] **Step 3: 提交失败测试前先保留工作树状态，不提交**

Run: `cd /home/weijiali/phi_ws/vibe_coding/claude_history && git status --short`
Expected: 输出包含 `?? web/src/views/PlansView.test.js`，确认测试已写入且尚未提交

### Task 4: 实现三栏 Plans 页面并让测试通过

**Files:**
- Modify: `web/src/views/PlansView.vue`
- Test: `web/src/views/PlansView.test.js`
- Test: `web/src/utils/planMetadata.test.js`

- [ ] **Step 1: 用三栏布局和筛选状态重写 `PlansView.vue`**

```vue
<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { marked } from 'marked'
import 'highlight.js/styles/github-dark.css'
import hljs from 'highlight.js'
import { enrichPlan, filterAndSortPlans, resolveSelectedPlanName } from '../utils/planMetadata'

const renderer = new marked.Renderer()
renderer.code = function({ text, lang }) {
  const language = lang || ''
  const highlighted = language && hljs.getLanguage(language)
    ? hljs.highlight(text, { language }).value
    : hljs.highlightAuto(text).value
  return `<div class="my-4 rounded-xl overflow-hidden border border-[var(--border-color)]"><div class="flex items-center justify-between px-4 py-2 bg-[var(--bg-card)] border-b border-[var(--border-color)]"><span class="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wide">${language || 'code'}</span></div><pre class="!m-0 !bg-[#0a0a0a] !rounded-t-none !rounded-b-xl !border-t-0 !p-4 overflow-x-auto"><code class="language-${language} text-sm">${highlighted}</code></pre></div>`
}
marked.setOptions({ renderer })

const plans = ref([])
const loading = ref(true)
const selectedPlanName = ref(null)
const searchQuery = ref('')
const sortBy = ref('modified')
const timeRange = ref('all')

const filteredPlans = computed(() =>
  filterAndSortPlans(plans.value, {
    query: searchQuery.value,
    sortBy: sortBy.value,
    timeRange: timeRange.value,
  })
)

const selectedPlan = computed(() =>
  filteredPlans.value.find(plan => plan.name === selectedPlanName.value) || null
)

const renderedMarkdown = computed(() =>
  selectedPlan.value?.content ? marked.parse(selectedPlan.value.content) : ''
)

watch(filteredPlans, (nextPlans) => {
  selectedPlanName.value = resolveSelectedPlanName(selectedPlanName.value, nextPlans)
})

onMounted(async () => {
  const res = await fetch('/api/plans')
  const basePlans = await res.json()

  const detailedPlans = await Promise.all(
    basePlans.map(async (plan) => {
      const detailRes = await fetch(`/api/plans/${plan.name}`)
      const detail = await detailRes.json()
      return enrichPlan(plan, detail.content)
    })
  )

  plans.value = detailedPlans
  selectedPlanName.value = resolveSelectedPlanName(null, filteredPlans.value)
  loading.value = false
})

function formatDate(ts) {
  return new Date(ts * 1000).toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  return `${(bytes / 1024).toFixed(1)} KB`
}
</script>

<template>
  <div class="flex flex-col h-full bg-[var(--bg-page)]">
    <div class="flex-shrink-0 h-14 border-b border-[var(--border-color)] flex items-center px-6 gap-4 bg-[var(--bg-page)]">
      <h1 class="text-lg font-semibold text-[var(--text-primary)]">Plans</h1>
      <span class="text-sm text-[var(--text-secondary)]">{{ plans.length }}</span>
    </div>

    <div v-if="loading" class="flex-1 flex items-center justify-center text-[var(--text-secondary)]">
      Loading plans...
    </div>

    <div v-else-if="plans.length === 0" class="flex-1 flex items-center justify-center text-[var(--text-secondary)]">
      No plans found.
    </div>

    <div v-else class="flex-1 min-h-0 grid grid-cols-[260px_minmax(320px,420px)_1fr]">
      <aside class="border-r border-[var(--border-color)] bg-[var(--bg-sidebar)] p-4 space-y-4 overflow-y-auto">
        <div>
          <label class="block text-xs font-medium text-[var(--text-secondary)] mb-2">Search</label>
          <input
            v-model="searchQuery"
            type="search"
            placeholder="Search title, filename, summary"
            class="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none"
          >
        </div>

        <div>
          <label class="block text-xs font-medium text-[var(--text-secondary)] mb-2">Sort by</label>
          <select v-model="sortBy" class="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] px-3 py-2 text-sm text-[var(--text-primary)]">
            <option value="modified">Recently modified</option>
            <option value="name">Filename</option>
            <option value="size">Size</option>
          </select>
        </div>

        <div>
          <label class="block text-xs font-medium text-[var(--text-secondary)] mb-2">Time range</label>
          <select v-model="timeRange" class="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] px-3 py-2 text-sm text-[var(--text-primary)]">
            <option value="all">All</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
          </select>
        </div>
      </aside>

      <section class="border-r border-[var(--border-color)] bg-[var(--bg-page)] overflow-y-auto p-4">
        <div v-if="filteredPlans.length === 0" class="rounded-xl border border-dashed border-[var(--border-color)] p-6 text-sm text-[var(--text-secondary)]">
          No plans match the current filters.
        </div>

        <div v-else class="space-y-3">
          <button
            v-for="plan in filteredPlans"
            :key="plan.name"
            @click="selectedPlanName = plan.name"
            :class="plan.name === selectedPlanName ? 'border-blue-500 bg-blue-500/8' : 'border-[var(--border-color)] bg-[var(--bg-card)] hover:border-blue-400/40'"
            class="w-full rounded-xl border p-4 text-left transition-colors"
          >
            <div class="text-sm font-semibold text-[var(--text-primary)] line-clamp-1">{{ plan.displayTitle }}</div>
            <div class="mt-1 text-xs font-mono text-[var(--text-secondary)] line-clamp-1">{{ plan.filename }}</div>
            <div class="mt-3 flex items-center gap-3 text-xs text-[var(--text-secondary)]">
              <span>{{ formatDate(plan.modified) }}</span>
              <span>{{ formatSize(plan.size) }}</span>
            </div>
            <p class="mt-3 text-sm text-[var(--text-secondary)] line-clamp-3">{{ plan.summary }}</p>
          </button>
        </div>
      </section>

      <section class="overflow-y-auto px-6 py-8">
        <div v-if="!selectedPlan" class="h-full flex items-center justify-center text-[var(--text-secondary)] text-sm">
          Select a plan from the list to preview its content.
        </div>
        <article v-else class="prose prose-sm max-w-none" v-html="renderedMarkdown"></article>
      </section>
    </div>
  </div>
</template>

<style scoped>
:deep(.prose) {
  --tw-prose-body: var(--text-primary);
  --tw-prose-headings: var(--text-primary);
  --tw-prose-links: #3b82f6;
  --tw-prose-bold: var(--text-primary);
  --tw-prose-counters: var(--text-secondary);
  --tw-prose-bullets: var(--text-secondary);
  --tw-prose-hr: var(--border-color);
  --tw-prose-quotes: var(--text-primary);
  --tw-prose-quote-borders: #8b5cf6;
  --tw-prose-code: #9333ea;
}

.dark :deep(.prose) {
  --tw-prose-code: #f0abfc;
  --tw-prose-links: #60a5fa;
}

:deep(.prose h1) {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 1.5rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border-color);
}

:deep(.prose h2) {
  font-size: 1.25rem;
  font-weight: 600;
  margin-top: 2rem;
  margin-bottom: 1rem;
}

:deep(.prose h3) {
  font-size: 1.125rem;
  font-weight: 500;
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
}

:deep(.prose p) {
  line-height: 1.625;
}

:deep(.prose ul),
:deep(.prose ol) {
  margin-top: 1rem;
  margin-bottom: 1rem;
}

:deep(.prose li) {
  line-height: 1.625;
  margin-top: 0.5rem;
}

:deep(.prose blockquote) {
  border-left: 4px solid #a855f7;
  padding-left: 1rem;
  margin-top: 1rem;
  margin-bottom: 1rem;
  font-style: italic;
}

:deep(.prose code:not(pre code)) {
  background-color: var(--bg-card);
  color: #a855f7;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
}

.dark :deep(.prose code:not(pre code)) {
  color: #f0abfc;
}

:deep(.prose a) {
  text-decoration: underline;
  text-underline-offset: 2px;
}

:deep(.prose a:hover) {
  color: #a855f7;
}

:deep(.prose table) {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
  margin-bottom: 1rem;
}

:deep(.prose th),
:deep(.prose td) {
  border: 1px solid var(--border-color);
  padding: 0.5rem 0.75rem;
  text-align: left;
}

:deep(.prose th) {
  background-color: var(--bg-card);
  font-weight: 600;
}

:deep(.prose tbody tr:nth-child(odd)) {
  background-color: rgba(var(--bg-card), 0.5);
}

:deep(.prose pre) {
  background-color: #1e1e1e !important;
  border-radius: 0.75rem;
  border: 1px solid var(--border-color);
  margin-top: 1rem;
  margin-bottom: 1rem;
  padding: 1rem;
  overflow-x: auto;
}

:deep(.prose pre code) {
  background: transparent;
  color: #d4d4d4;
  font-size: 0.875rem;
  line-height: 1.6;
}
</style>
```

- [ ] **Step 2: 运行组件测试确认通过**

Run: `cd /home/weijiali/phi_ws/vibe_coding/claude_history/web && npm run test:run -- src/views/PlansView.test.js`
Expected: PASS，输出包含 `3 passed`

- [ ] **Step 3: 运行纯函数测试回归**

Run: `cd /home/weijiali/phi_ws/vibe_coding/claude_history/web && npm run test:run -- src/utils/planMetadata.test.js`
Expected: PASS，输出包含 `5 passed`

- [ ] **Step 4: 运行完整前端测试集**

Run: `cd /home/weijiali/phi_ws/vibe_coding/claude_history/web && npm run test:run`
Expected: PASS，输出包含 `8 passed`

- [ ] **Step 5: 构建前端确认生产包可通过**

Run: `cd /home/weijiali/phi_ws/vibe_coding/claude_history/web && npm run build`
Expected: PASS，输出包含 `vite v6` 和 `built in`

- [ ] **Step 6: 手动验证 Plans 页交互**

Run: `cd /home/weijiali/phi_ws/vibe_coding/claude_history && ./start.sh`
Expected: 前后端都启动成功；在浏览器访问 `/plans` 后手动确认以下事项：
- 默认展示三栏布局，不再出现顶部横向 tab 列表
- 左侧可以输入搜索词并改变排序、时间范围
- 中间卡片显示标题、文件名、修改时间、大小、摘要
- 过滤后如果当前选中项消失，右侧自动切到第一条结果
- 没有匹配结果时显示 `No plans match the current filters.` 和空预览提示

- [ ] **Step 7: 提交页面重构改动**

```bash
cd /home/weijiali/phi_ws/vibe_coding/claude_history
git add web/src/utils/planMetadata.js web/src/utils/planMetadata.test.js web/src/views/PlansView.test.js web/src/views/PlansView.vue
git commit -m "feat: 重构 Plans 页面管理视图"
```

## Self-Review Checklist

- Spec coverage:
  - 三栏布局：Task 4 Step 1
  - 标题/文件名/摘要搜索：Task 2 Step 3 + Task 4 Step 1
  - 排序与时间筛选：Task 2 Step 3 + Task 4 Step 1
  - 当前选中项过滤后自动切换：Task 2 Step 3 + Task 3 Step 1 + Task 4 Step 1
  - 保留 Markdown 渲染：Task 4 Step 1
  - 不改后端接口：所有任务都只修改 `web/` 下文件
- Placeholder scan: 已避免使用 TBD/TODO/“自行处理”等占位语句。
- Type consistency: 计划中统一使用 `displayTitle`、`summary`、`searchText`、`filteredPlans`、`selectedPlanName` 这些字段名。
