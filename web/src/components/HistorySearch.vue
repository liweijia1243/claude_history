<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = defineProps({
  projectPath: { type: String, default: '' },
  syncUrl: { type: Boolean, default: true },
  showProject: { type: Boolean, default: true },
  initiallyActive: { type: Boolean, default: true },
})

const emit = defineEmits(['search-active'])

const items = ref([])
const total = ref(0)
const page = ref(1)
const pages = ref(0)
const search = ref('')
const loading = ref(false)
const searchTimeout = ref(null)
const blurTimeout = ref(null)
const active = ref(props.initiallyActive)
const hasLoaded = ref(false)

const route = useRoute()
const router = useRouter()

// Restore search from URL query on mount (only when syncUrl is true)
if (props.syncUrl) {
  const initialSearch = route.query.q || ''
  search.value = initialSearch
}

const expandedItems = ref(new Set())
const clickTimer = ref(null)

async function fetchHistory() {
  loading.value = true
  const params = new URLSearchParams({
    page: page.value,
    limit: 50,
    ...(search.value ? { search: search.value } : {}),
    ...(props.projectPath ? { project: props.projectPath } : {}),
  })
  const res = await fetch(`/api/history?${params}`)
  const data = await res.json()
  items.value = data.items
  total.value = data.total
  pages.value = data.pages
  loading.value = false
  hasLoaded.value = true
}

function onSearchInput() {
  clearTimeout(searchTimeout.value)
  clearTimeout(blurTimeout.value)
  searchTimeout.value = setTimeout(() => {
    page.value = 1
    if (props.syncUrl) {
      router.replace({ path: '/history', query: search.value ? { q: search.value } : {} })
    }
    fetchHistory()
  }, 300)
}

function onFocus() {
  clearTimeout(blurTimeout.value)
  if (!active.value) {
    active.value = true
    emit('search-active', true)
  }
  if (!hasLoaded.value) {
    fetchHistory()
  }
}

function onBlur() {
  clearTimeout(blurTimeout.value)
  blurTimeout.value = setTimeout(() => {
    if (!search.value) {
      active.value = false
      emit('search-active', false)
    }
  }, 200)
}

function handleClick(item) {
  clearTimeout(clickTimer.value)
  clickTimer.value = setTimeout(() => {
    const key = item.timestamp
    if (expandedItems.value.has(key)) {
      expandedItems.value.delete(key)
    } else {
      expandedItems.value.add(key)
    }
    expandedItems.value = new Set(expandedItems.value)
  }, 250)
}

function handleDblClick(item) {
  clearTimeout(clickTimer.value)
  navigateToConversation(item)
}

function navigateToConversation(item) {
  const projectId = item.project_id
  const sessionId = item.sessionId
  if (!projectId || !sessionId) return

  const source = props.projectPath ? 'project' : 'history'
  const query = {
    msgTimestamp: String(item.timestamp),
    source,
  }
  if (search.value) {
    query.q = search.value
  }
  router.push({
    path: `/projects/${projectId}/sessions/${sessionId}`,
    query,
  })
}

function formatFullTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatDate(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)

  if (d.toDateString() === today.toDateString()) {
    return 'Today'
  } else if (d.toDateString() === yesterday.toDateString()) {
    return 'Yesterday'
  }
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function formatProject(p) {
  if (!p) return ''
  return p.split('/').slice(-2).join('/')
}

const groupedItems = computed(() => {
  const groups = {}
  for (const item of items.value) {
    const dateKey = formatDate(item.timestamp)
    if (!groups[dateKey]) {
      groups[dateKey] = []
    }
    groups[dateKey].push(item)
  }
  return groups
})

onMounted(() => {
  if (props.initiallyActive) {
    fetchHistory()
  }
})
watch(page, fetchHistory)
</script>

<template>
  <!-- Search -->
  <div class="mb-6">
    <div class="relative">
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-secondary)]"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
      <input
        v-model="search"
        @input="onSearchInput"
        @focus="onFocus"
        @blur="onBlur"
        placeholder="Search commands..."
        class="w-full bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl pl-10 pr-4 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:outline-none focus:border-blue-500/50 transition-colors"
      />
    </div>
  </div>

  <!-- Results area: show when active (focused or has search content) -->
  <template v-if="active">
    <div v-if="loading" class="text-[var(--text-secondary)] py-8 text-center">Loading...</div>

    <div v-else class="space-y-8">
      <div v-for="(groupItems, dateLabel) in groupedItems" :key="dateLabel">
        <!-- Date header -->
        <div class="flex items-center gap-3 mb-4">
          <h2 class="text-sm font-semibold text-[var(--text-secondary)]">{{ dateLabel }}</h2>
          <div class="flex-1 h-px bg-[var(--border-color)]"></div>
          <span class="text-xs text-[var(--text-secondary)]">{{ groupItems.length }}</span>
        </div>

        <!-- Timeline items -->
        <div class="relative pl-6">
          <div class="absolute left-[7px] top-0 bottom-0 w-px bg-[var(--border-color)]"></div>

          <div
            v-for="item in groupItems"
            :key="item.timestamp"
            class="relative pb-4 last:pb-0"
          >
            <div class="absolute -left-6 top-2 w-3.5 h-3.5 rounded-full border-2 border-[var(--border-color)] bg-[var(--bg-page)]"></div>

            <div
              class="bg-[var(--bg-card)]/50 rounded-lg px-4 py-3 hover:bg-[var(--bg-card)] transition-colors border border-transparent hover:border-[var(--border-color)] cursor-pointer"
              @click="handleClick(item)"
              @dblclick="handleDblClick(item)"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="flex-1 min-w-0">
                  <p class="text-sm text-[var(--text-primary)] break-words whitespace-pre-wrap leading-relaxed">{{ item.display }}</p>
                  <div v-if="showProject" class="flex items-center gap-3 mt-2">
                    <span
                      v-if="item.project"
                      class="inline-flex items-center gap-1 text-xs text-[var(--text-secondary)] bg-[var(--bg-assistant)] px-2 py-0.5 rounded-full"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>
                      {{ formatProject(item.project) }}
                    </span>
                  </div>
                </div>
                <span class="text-xs text-[var(--text-secondary)] flex-shrink-0 whitespace-nowrap">{{ formatTime(item.timestamp) }}</span>
              </div>
              <div v-if="expandedItems.has(item.timestamp)" class="mt-3 pt-3 border-t border-[var(--border-color)] space-y-1.5">
                <div class="text-xs text-[var(--text-secondary)]">
                  <span class="font-medium">Full path:</span> {{ item.project }}
                </div>
                <div class="text-xs text-[var(--text-secondary)]">
                  <span class="font-medium">Time:</span> {{ formatFullTime(item.timestamp) }}
                </div>
                <div class="text-xs text-[var(--text-secondary)]">
                  <span class="font-medium">Session:</span> {{ item.sessionId?.substring(0, 16) }}...
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="pages > 1" class="flex items-center justify-center gap-2 mt-8">
      <button
        @click="page = Math.max(1, page - 1)"
        :disabled="page <= 1"
        class="px-4 py-2 rounded-lg text-sm bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-blue-500/50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        Previous
      </button>
      <span class="text-sm text-[var(--text-secondary)] px-3">{{ page }} / {{ pages }}</span>
      <button
        @click="page = Math.min(pages, page + 1)"
        :disabled="page >= pages"
        class="px-4 py-2 rounded-lg text-sm bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-blue-500/50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        Next
      </button>
    </div>
  </template>
</template>
