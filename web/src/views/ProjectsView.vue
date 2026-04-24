<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiPath, routePath, sourceFromRoute } from '../utils/source'

const router = useRouter()
const route = useRoute()
const source = computed(() => sourceFromRoute(route))
const projects = ref([])
const loading = ref(true)
const searchQuery = ref('')

const filteredProjects = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  if (!q) return projects.value
  return projects.value.filter(p => p.path.toLowerCase().includes(q))
})

async function fetchProjects() {
  loading.value = true
  const res = await fetch(apiPath(source.value, '/projects'))
  projects.value = await res.json()
  loading.value = false
}

onMounted(async () => {
  await fetchProjects()
})

watch(source, () => {
  fetchProjects()
})

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

function projectName(path) {
  const parts = path.split('/')
  return parts[parts.length - 1] || path
}

function projectParent(path) {
  const parts = path.split('/')
  if (parts.length <= 1) return ''
  return parts.slice(0, -1).join('/')
}

function openProject(projectId) {
  router.push(routePath(source.value, `/projects/${projectId}`))
}
</script>

<template>
  <div class="p-6 max-w-6xl mx-auto">
    <h1 class="text-2xl font-bold text-[var(--text-primary)] mb-6 flex items-center gap-3">
      Projects
      <span class="text-sm font-normal text-[var(--text-secondary)]">
        {{ searchQuery ? filteredProjects.length + '/' + projects.length : projects.length }}
      </span>
    </h1>

    <div v-if="!loading" class="relative mb-4">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-secondary)]">
        <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
      </svg>
      <input
        v-model="searchQuery"
        type="text"
        placeholder="搜索项目路径..."
        class="w-full pl-10 pr-9 py-2.5 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] text-[var(--text-primary)] placeholder:text-[var(--text-secondary)] focus:outline-none focus:border-purple-400/50 transition-colors"
      />
      <button
        v-if="searchQuery"
        @click="searchQuery = ''"
        class="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
      </button>
    </div>

    <div v-if="loading" class="text-[var(--text-secondary)] py-8 text-center">Loading...</div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <button
        v-for="project in filteredProjects"
        :key="project.id"
        @click="openProject(project.id)"
        class="text-left p-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] hover:bg-[var(--bg-assistant)] transition-colors"
      >
        <div class="flex items-center gap-2 mb-2">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-purple-400 flex-shrink-0"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>
          <span class="font-medium text-sm text-[var(--text-primary)] truncate" :title="project.path">
            {{ projectName(project.path) }}
          </span>
        </div>
        <div class="text-xs text-[var(--text-secondary)] truncate mb-2" :title="project.path">
          {{ projectParent(project.path) }}
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

    <div v-if="!loading && searchQuery && filteredProjects.length === 0" class="text-center py-12 text-[var(--text-secondary)]">
      <p>未找到匹配 "{{ searchQuery }}" 的项目</p>
    </div>
  </div>
</template>
