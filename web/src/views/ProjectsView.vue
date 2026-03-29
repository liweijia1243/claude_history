<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const projects = ref([])
const loading = ref(true)

onMounted(async () => {
  const res = await fetch('/api/projects')
  projects.value = await res.json()
  loading.value = false
})

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

function truncatePath(path) {
  const parts = path.split('/')
  if (parts.length <= 3) return path
  return '.../' + parts.slice(-3).join('/')
}

function openProject(projectId) {
  router.push(`/projects/${projectId}`)
}
</script>

<template>
  <div class="p-6 max-w-6xl mx-auto">
    <h1 class="text-2xl font-bold text-[var(--text-primary)] mb-6 flex items-center gap-3">
      Projects
      <span class="text-sm font-normal text-[var(--text-secondary)]">{{ projects.length }}</span>
    </h1>

    <div v-if="loading" class="text-[var(--text-secondary)] py-8 text-center">Loading...</div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <button
        v-for="project in projects"
        :key="project.id"
        @click="openProject(project.id)"
        class="text-left p-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] hover:bg-[var(--bg-assistant)] transition-colors"
      >
        <div class="flex items-center gap-2 mb-2">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-purple-400 flex-shrink-0"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>
          <span class="font-medium text-sm text-[var(--text-primary)] truncate" :title="project.path">
            {{ truncatePath(project.path) }}
          </span>
        </div>
        <div class="flex items-center gap-3 text-xs text-[var(--text-secondary)]">
          <span class="flex items-center gap-1">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/></svg>
            {{ project.session_count }} sessions
          </span>
          <span>{{ formatSize(project.size) }}</span>
        </div>
      </button>
    </div>
  </div>
</template>
