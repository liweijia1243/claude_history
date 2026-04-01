<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import HistorySearch from '../components/HistorySearch.vue'

const props = defineProps({
  projectId: String
})

const route = useRoute()
const router = useRouter()
const project = ref(null)
const sessions = ref([])
const loading = ref(true)
const searchActive = ref(false)

onMounted(async () => {
  const res = await fetch(`/api/projects/${props.projectId}`)
  if (!res.ok) {
    router.push('/projects')
    return
  }
  const data = await res.json()
  project.value = data
  sessions.value = data.sessions
  loading.value = false
})

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function goBack() {
  router.push('/projects')
}

function openSession(sessionId) {
  router.push(`/projects/${props.projectId}/sessions/${sessionId}`)
}

function onSearchActive(active) {
  searchActive.value = active
}
</script>

<template>
  <div class="flex flex-col h-full bg-[var(--bg-page)]">
    <!-- Header -->
    <div class="flex-shrink-0 h-12 border-b border-[var(--border-color)] flex items-center px-4 gap-4 bg-[var(--bg-sidebar)]">
      <button
        @click="goBack"
        class="flex items-center gap-1.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors text-sm"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>
        Back
      </button>
      <div class="flex-1 min-w-0 flex items-center gap-3">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-purple-400 flex-shrink-0"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>
        <span class="font-mono text-sm text-[var(--text-primary)] truncate" :title="project?.path">
          {{ project?.path }}
        </span>
      </div>
      <span class="text-xs text-[var(--text-secondary)]">{{ sessions.length }} sessions</span>
    </div>

    <!-- Content area -->
    <div class="flex-1 overflow-auto">
      <!-- Search bar + results (always rendered, single instance) -->
      <div class="p-6 max-w-5xl mx-auto">
        <HistorySearch
          :project-path="project?.path || ''"
          :sync-url="false"
          :show-project="false"
          :initially-active="false"
          @search-active="onSearchActive"
        />
      </div>

      <!-- Session list (shown when search is inactive) -->
      <div v-if="!searchActive">
        <div v-if="loading" class="text-[var(--text-secondary)] text-center py-16">Loading...</div>

        <div v-else-if="sessions.length === 0" class="text-[var(--text-secondary)] text-center py-16">
          No sessions found
        </div>

        <div v-else class="max-w-3xl mx-auto pb-6 px-6 space-y-3">
          <button
            v-for="session in sessions"
            :key="session.id"
            @click="openSession(session.id)"
            class="w-full text-left p-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] hover:bg-[var(--bg-assistant)] transition-colors"
          >
            <div class="font-mono text-xs text-[var(--text-secondary)] mb-1">
              {{ session.id }}
            </div>
            <div v-if="session.preview" class="text-sm text-[var(--text-primary)] truncate">
              {{ session.preview }}
            </div>
            <div v-else class="text-sm text-[var(--text-secondary)] italic">No preview</div>
            <div class="flex justify-between mt-2 text-xs text-[var(--text-secondary)]">
              <span>{{ session.message_count }} messages</span>
              <span>{{ formatTime(session.modified) }}</span>
            </div>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
