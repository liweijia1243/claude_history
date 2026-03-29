<script setup>
import { ref, onMounted, computed } from 'vue'
import { marked } from 'marked'
import 'highlight.js/styles/github-dark.css'
import hljs from 'highlight.js'

// Custom renderer for code blocks
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
const selectedPlan = ref(null)
const planContent = ref('')
const loading = ref(true)

onMounted(async () => {
  const res = await fetch('/api/plans')
  plans.value = await res.json()
  loading.value = false
  // Auto-select first plan
  if (plans.value.length > 0) {
    selectPlan(plans.value[0])
  }
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
  if (bytes < 1024) return bytes + ' B'
  return (bytes / 1024).toFixed(1) + ' KB'
}

async function selectPlan(plan) {
  selectedPlan.value = plan.name
  const res = await fetch(`/api/plans/${plan.name}`)
  const data = await res.json()
  planContent.value = data.content
}

function renderedMarkdown() {
  if (!planContent.value) return ''
  return marked.parse(planContent.value)
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Header with tabs -->
    <div class="flex-shrink-0 h-14 border-b border-[var(--border-color)] flex items-center px-6 gap-4 bg-[var(--bg-page)]">
      <h1 class="text-lg font-semibold text-[var(--text-primary)]">Plans</h1>
      <span class="text-sm text-[var(--text-secondary)]">{{ plans.length }}</span>
    </div>

    <!-- Tab bar -->
    <div v-if="!loading && plans.length > 0" class="flex-shrink-0 border-b border-[var(--border-color)] bg-[var(--bg-page)] px-6">
      <div class="flex gap-1 -mb-px overflow-x-auto py-2">
        <button
          v-for="plan in plans"
          :key="plan.name"
          @click="selectPlan(plan)"
          :class="[
            selectedPlan === plan.name
              ? 'border-blue-500 text-[var(--text-primary)] bg-[var(--bg-card)]'
              : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-color)]'
          ]"
          class="flex items-center gap-2 px-4 py-2 border-b-2 text-sm font-medium transition-colors whitespace-nowrap rounded-t-lg"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="opacity-60"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/></svg>
          {{ plan.name }}
          <span class="text-xs text-[var(--text-secondary)]">{{ formatSize(plan.size) }}</span>
        </button>
      </div>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-auto">
      <div v-if="loading" class="text-[var(--text-secondary)] p-8 text-center">Loading...</div>

      <div v-else-if="plans.length === 0" class="text-[var(--text-secondary)] p-8 text-center">No plans found.</div>

      <div v-else-if="selectedPlan && planContent" class="max-w-4xl mx-auto py-8 px-6">
        <article
          class="prose prose-sm max-w-none"
          v-html="renderedMarkdown()"
        ></article>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Prose customization */
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

/* Code block styling - always dark background */
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
