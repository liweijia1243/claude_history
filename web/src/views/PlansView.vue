<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { marked } from 'marked'
import 'highlight.js/styles/github-dark.css'
import hljs from 'highlight.js'

import { enrichPlan, filterAndSortPlans, resolveSelectedPlanName } from '../utils/planMetadata'

const SORT_OPTIONS = [
  { value: 'modified', label: '最近更新' },
  { value: 'name', label: '文件名' },
  { value: 'size', label: '文件大小' },
]

const TIME_RANGE_OPTIONS = [
  { value: 'all', label: '全部时间' },
  { value: '24h', label: '最近 24 小时' },
  { value: '7d', label: '最近 7 天' },
  { value: '30d', label: '最近 30 天' },
]

const renderer = new marked.Renderer()
renderer.code = function({ text, lang }) {
  const language = lang || ''
  const highlighted = language && hljs.getLanguage(language)
    ? hljs.highlight(text, { language }).value
    : hljs.highlightAuto(text).value
  return `<div class="my-4 rounded-xl overflow-hidden border border-[var(--border-color)]"><div class="flex items-center justify-between px-4 py-2 bg-[var(--bg-card)] border-b border-[var(--border-color)]"><span class="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wide">${language || 'code'}</span></div><pre class="!m-0 !bg-[#0a0a0a] !rounded-t-none !rounded-b-xl !border-t-0 !p-4 overflow-x-auto"><code class="language-${language} text-sm">${highlighted}</code></pre></div>`
}

marked.setOptions({
  renderer,
})

const plans = ref([])
const selectedPlanName = ref(null)
const loading = ref(true)
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
  filteredPlans.value.find((plan) => plan.name === selectedPlanName.value) ?? null
)

const renderedMarkdown = computed(() => {
  if (!selectedPlan.value?.content) {
    return ''
  }

  return marked.parse(selectedPlan.value.content)
})

watch(
  filteredPlans,
  (nextPlans) => {
    selectedPlanName.value = resolveSelectedPlanName(selectedPlanName.value, nextPlans)
  },
  { immediate: true }
)

onMounted(async () => {
  loading.value = true

  try {
    const res = await fetch('/api/plans')
    const rawPlans = await res.json()
    const detailedPlans = await Promise.all(
      rawPlans.map(async (plan) => {
        const detailRes = await fetch(`/api/plans/${plan.name}`)
        const detail = await detailRes.json()
        return enrichPlan(plan, detail.content)
      })
    )

    plans.value = detailedPlans
  } finally {
    loading.value = false
  }
})

function formatDate(value) {
  if (value == null) {
    return '未知时间'
  }

  const normalized = typeof value === 'number' && value < 1e12 ? value * 1000 : value
  const date = new Date(normalized)

  if (Number.isNaN(date.getTime())) {
    return '未知时间'
  }

  return date.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatSize(bytes) {
  const size = Number(bytes)

  if (!Number.isFinite(size) || size < 0) {
    return '未知大小'
  }

  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

function selectPlan(planName) {
  selectedPlanName.value = planName
}
</script>

<template>
  <div class="flex h-full flex-col">
    <div class="flex h-14 flex-shrink-0 items-center gap-4 border-b border-[var(--border-color)] bg-[var(--bg-page)] px-6">
      <h1 class="text-lg font-semibold text-[var(--text-primary)]">Plans</h1>
      <span class="text-sm text-[var(--text-secondary)]">{{ filteredPlans.length }} / {{ plans.length }}</span>
    </div>

    <div class="flex min-h-0 flex-1">
      <aside class="w-72 flex-shrink-0 border-r border-[var(--border-color)] bg-[var(--bg-page)] p-5">
        <div class="space-y-5">
          <section>
            <label class="mb-2 block text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              搜索
            </label>
            <input
              v-model="searchQuery"
              type="search"
              placeholder="搜索标题、文件名或摘要"
              class="w-full rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition focus:border-blue-500"
            />
          </section>

          <section>
            <label class="mb-2 block text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              排序
            </label>
            <select
              v-model="sortBy"
              class="w-full rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition focus:border-blue-500"
            >
              <option v-for="option in SORT_OPTIONS" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </section>

          <section>
            <label class="mb-2 block text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              时间范围
            </label>
            <select
              v-model="timeRange"
              class="w-full rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition focus:border-blue-500"
            >
              <option v-for="option in TIME_RANGE_OPTIONS" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </section>
        </div>
      </aside>

      <section class="flex min-h-0 w-[28rem] flex-shrink-0 flex-col border-r border-[var(--border-color)] bg-[var(--bg-page)]">
        <div class="border-b border-[var(--border-color)] px-5 py-4">
          <p class="text-sm text-[var(--text-secondary)]">计划列表</p>
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto p-4">
          <div v-if="loading" class="rounded-2xl border border-dashed border-[var(--border-color)] p-6 text-center text-sm text-[var(--text-secondary)]">
            Loading...
          </div>

          <div v-else-if="filteredPlans.length === 0" class="rounded-2xl border border-dashed border-[var(--border-color)] p-6 text-center text-sm text-[var(--text-secondary)]">
            No plans match the current filters.
          </div>

          <div v-else class="space-y-3">
            <button
              v-for="plan in filteredPlans"
              :key="plan.name"
              :title="plan.name"
              type="button"
              @click="selectPlan(plan.name)"
              :class="selectedPlanName === plan.name
                ? 'border-blue-500 bg-blue-500/10 shadow-sm'
                : 'border-[var(--border-color)] bg-[var(--bg-card)] hover:border-blue-400/60 hover:bg-[var(--bg-hover)]'"
              class="block w-full rounded-2xl border p-4 text-left transition"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0 flex-1">
                  <h2 class="truncate text-sm font-semibold text-[var(--text-primary)]">{{ plan.displayTitle }}</h2>
                  <p class="mt-1 truncate text-xs text-[var(--text-secondary)]">{{ plan.filename || plan.name }}</p>
                </div>
                <span class="rounded-full bg-[var(--bg-page)] px-2 py-1 text-[11px] text-[var(--text-secondary)]">
                  {{ formatSize(plan.size) }}
                </span>
              </div>

              <div class="mt-3 flex items-center justify-between gap-3 text-xs text-[var(--text-secondary)]">
                <span>{{ formatDate(plan.modified) }}</span>
              </div>

              <p class="mt-3 line-clamp-3 text-sm leading-6 text-[var(--text-secondary)]">
                {{ plan.summary }}
              </p>
            </button>
          </div>
        </div>
      </section>

      <section class="min-h-0 min-w-0 flex-1 bg-[var(--bg-page)]">
        <div class="flex h-full flex-col">
          <div class="flex items-center justify-between border-b border-[var(--border-color)] px-6 py-4">
            <div>
              <p class="text-sm font-semibold text-[var(--text-primary)]">
                {{ selectedPlan?.displayTitle || '预览' }}
              </p>
              <p v-if="selectedPlan" class="mt-1 text-xs text-[var(--text-secondary)]">
                {{ selectedPlan.filename || selectedPlan.name }}
              </p>
            </div>
          </div>

          <div class="min-h-0 flex-1 overflow-y-auto">
            <div v-if="loading" class="p-8 text-center text-[var(--text-secondary)]">Loading...</div>

            <div v-else-if="!selectedPlan" class="flex h-full items-center justify-center p-8 text-center text-sm text-[var(--text-secondary)]">
              No plans match the current filters.
            </div>

            <div v-else class="mx-auto max-w-4xl px-6 py-8">
              <article class="plan-preview prose prose-sm max-w-none" v-html="renderedMarkdown"></article>
            </div>
          </div>
        </div>
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
