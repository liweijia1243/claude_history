<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const stats = ref(null)
const recentSessions = ref([])
const loading = ref(true)

onMounted(async () => {
  const [statsRes, sessionsRes] = await Promise.all([
    fetch('/api/stats'),
    fetch('/api/recent-sessions?limit=5')
  ])
  stats.value = await statsRes.json()
  recentSessions.value = await sessionsRes.json()
  loading.value = false
})

function formatNumber(n) {
  return n?.toLocaleString() ?? '0'
}

function formatTime(ts) {
  if (!ts) return ''
  const d = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts)
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function openSession(session) {
  router.push(`/projects/${session.project_id}/sessions/${session.session_id}`)
}
</script>

<template>
  <div class="p-6 max-w-6xl mx-auto">
    <h1 class="text-2xl font-bold text-[var(--text-primary)] mb-6">Dashboard</h1>

    <div v-if="loading" class="text-[var(--text-secondary)]">Loading...</div>

    <div v-else-if="stats" class="space-y-6">
      <!-- Stats Grid -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- Total Commands -->
        <div class="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)] group hover:border-blue-500/30 transition-colors">
          <div class="flex items-center gap-3 mb-3">
            <div class="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-blue-400"><path d="m5 12 7-7 7 7"/><path d="M12 19V5"/></svg>
            </div>
            <span class="text-[var(--text-secondary)] text-sm">Commands</span>
          </div>
          <div class="text-3xl font-bold text-blue-400">{{ formatNumber(stats.total_commands) }}</div>
        </div>

        <!-- Sessions -->
        <div class="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)] group hover:border-green-500/30 transition-colors">
          <div class="flex items-center gap-3 mb-3">
            <div class="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-green-400"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><path d="M14 2v6h6"/></svg>
            </div>
            <span class="text-[var(--text-secondary)] text-sm">Sessions</span>
          </div>
          <div class="text-3xl font-bold text-green-400">{{ formatNumber(stats.total_sessions) }}</div>
        </div>

        <!-- Projects -->
        <div class="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)] group hover:border-purple-500/30 transition-colors">
          <div class="flex items-center gap-3 mb-3">
            <div class="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-purple-400"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>
            </div>
            <span class="text-[var(--text-secondary)] text-sm">Projects</span>
          </div>
          <div class="text-3xl font-bold text-purple-400">{{ formatNumber(stats.total_projects) }}</div>
        </div>

        <!-- Plans -->
        <div class="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)] group hover:border-amber-500/30 transition-colors">
          <div class="flex items-center gap-3 mb-3">
            <div class="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-amber-400"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14,2 14,8 20,8"/></svg>
            </div>
            <span class="text-[var(--text-secondary)] text-sm">Plans</span>
          </div>
          <div class="text-3xl font-bold text-amber-400">{{ formatNumber(stats.total_plans) }}</div>
        </div>
      </div>

      <!-- Recent Activity -->
      <div class="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
        <div class="text-[var(--text-secondary)] text-sm mb-2">Commands in last 24h</div>
        <div class="text-xl font-semibold text-[var(--text-primary)]">{{ stats.recent_commands_24h }}</div>
      </div>

      <!-- Recent Sessions -->
      <div class="bg-[var(--bg-card)] rounded-xl border border-[var(--border-color)] overflow-hidden">
        <div class="px-5 py-4 border-b border-[var(--border-color)] flex items-center justify-between">
          <h2 class="font-semibold text-[var(--text-primary)] flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-[var(--text-secondary)]"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
            Recent Sessions
          </h2>
          <router-link to="/projects" class="text-sm text-blue-400 hover:text-blue-300 transition-colors">View all</router-link>
        </div>

        <div v-if="recentSessions.length === 0" class="px-5 py-8 text-center text-[var(--text-secondary)]">
          No recent sessions
        </div>

        <div v-else class="divide-y divide-[var(--border-color)]">
          <button
            v-for="session in recentSessions"
            :key="session.session_id"
            @click="openSession(session)"
            class="w-full text-left px-5 py-3 hover:bg-[var(--bg-assistant)] transition-colors group"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="flex-1 min-w-0">
                <div class="text-sm text-[var(--text-primary)] truncate group-hover:text-blue-400 transition-colors">
                  {{ session.preview || 'No preview available' }}
                </div>
                <div class="flex items-center gap-3 mt-1.5">
                  <span class="text-xs text-[var(--text-secondary)] bg-[var(--bg-assistant)] px-2 py-0.5 rounded truncate max-w-[200px]">
                    {{ session.project_path }}
                  </span>
                  <span class="text-xs text-[var(--text-secondary)]">{{ session.message_count }} msgs</span>
                </div>
              </div>
              <span class="text-xs text-[var(--text-secondary)] whitespace-nowrap">{{ formatTime(session.timestamp) }}</span>
            </div>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
