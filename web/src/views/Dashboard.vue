<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import StatCard from '../components/dashboard/StatCard.vue'
import TrendChart from '../components/dashboard/TrendChart.vue'
import MessageTypeChart from '../components/dashboard/MessageTypeChart.vue'
import TopProjectsChart from '../components/dashboard/TopProjectsChart.vue'
import HourlyChart from '../components/dashboard/HourlyChart.vue'
import TokenUsageChart from '../components/dashboard/TokenUsageChart.vue'
import SessionDurationChart from '../components/dashboard/SessionDurationChart.vue'
import RecentSessions from '../components/dashboard/RecentSessions.vue'

const router = useRouter()
const dashboardStats = ref(null)
const recentSessions = ref([])
const loading = ref(true)
const range = ref('30d')

async function fetchDashboardStats() {
  const res = await fetch(`/api/dashboard-stats?range=${range.value}`)
  dashboardStats.value = await res.json()
}

async function fetchRecentSessions() {
  const res = await fetch('/api/recent-sessions?limit=4')
  recentSessions.value = await res.json()
}

onMounted(async () => {
  await Promise.all([fetchDashboardStats(), fetchRecentSessions()])
  loading.value = false
})

watch(range, () => {
  fetchDashboardStats()
})

// ── Sparkline data: last 7 entries from daily_series ──
const last7Days = computed(() => {
  const series = dashboardStats.value?.daily_series || []
  return series.slice(-7)
})

const commandsSparkline = computed(() => last7Days.value.map(d => d.commands))
const sessionsSparkline = computed(() => last7Days.value.map(d => d.sessions))
const tokensSparkline = computed(() => last7Days.value.map(d => d.tokens))

// Projects sparkline: just a flat count (no daily breakdown available)
const projectsSparkline = computed(() => [])

const totalTokens = computed(() => {
  const t = dashboardStats.value?.summary?.total_tokens
  return t ? t.input + t.output : 0
})

// ── Icons (inline SVG strings) ──
const icons = {
  commands: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12 7-7 7 7"/><path d="M12 19V5"/></svg>',
  sessions: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 8h8M8 12h6"/></svg>',
  projects: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>',
  tokens: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
}

function navigateToProject(projectId) {
  router.push(`/projects/${projectId}`)
}
</script>

<template>
  <div class="p-4 lg:p-6 max-w-7xl mx-auto">
    <h1 class="text-2xl font-bold text-[var(--text-primary)] mb-6">Dashboard</h1>

    <div v-if="loading" class="text-[var(--text-secondary)]">Loading...</div>

    <div v-else-if="dashboardStats" class="space-y-4 lg:space-y-6">
      <!-- Stats Cards -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4">
        <StatCard
          label="总命令数"
          :value="dashboardStats.summary.total_commands"
          color="#60a5fa"
          :icon="icons.commands"
          :change="dashboardStats.changes.commands_pct"
          change-label="vs 上周期"
          :sparkline-data="commandsSparkline"
        />
        <StatCard
          label="总会话数"
          :value="dashboardStats.summary.total_sessions"
          color="#4ade80"
          :icon="icons.sessions"
          :change="dashboardStats.changes.sessions_pct"
          change-label="vs 上周期"
          :sparkline-data="sessionsSparkline"
        />
        <StatCard
          label="项目数"
          :value="dashboardStats.summary.total_projects"
          color="#c084fc"
          :icon="icons.projects"
          :change="`+${dashboardStats.changes.projects_new}`"
          change-label="本周期新增"
          :sparkline-data="projectsSparkline"
        />
        <StatCard
          label="Token 用量"
          :value="totalTokens"
          color="#fbbf24"
          :icon="icons.tokens"
          :change="dashboardStats.changes.tokens_pct"
          change-label="vs 上周期"
          :sparkline-data="tokensSparkline"
          :invert-change-color="true"
        />
      </div>

      <!-- Trend Chart -->
      <TrendChart
        :daily-series="dashboardStats.daily_series"
        :range="range"
        @update:range="range = $event"
      />

      <!-- Bottom Row 1: Message Type / Top Projects / Hourly -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-3 lg:gap-4">
        <MessageTypeChart :message-types="dashboardStats.message_types" />
        <TopProjectsChart
          :top-projects="dashboardStats.top_projects"
          @navigate="navigateToProject"
        />
        <HourlyChart :hourly-distribution="dashboardStats.hourly_distribution" />
      </div>

      <!-- Bottom Row 2: Token Usage / Session Duration / Recent Sessions -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-3 lg:gap-4">
        <TokenUsageChart :total-tokens="dashboardStats.summary.total_tokens" />
        <SessionDurationChart :session-durations="dashboardStats.session_durations" />
        <RecentSessions :sessions="recentSessions" />
      </div>
    </div>
  </div>
</template>
