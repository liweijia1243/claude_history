<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  sessions: { type: Array, default: () => [] },
})

const router = useRouter()

function formatTime(ts) {
  if (!ts) return ''
  const d = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts)
  const now = new Date()
  const diffMs = now - d
  const diffH = diffMs / 3600000

  if (diffH < 24) {
    return d.toLocaleString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  if (diffH < 48) return '昨天'
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit' })
}

function openSession(session) {
  router.push(`/projects/${session.project_id}/sessions/${session.session_id}`)
}
</script>

<template>
  <div class="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
    <div class="flex items-center justify-between mb-3">
      <div class="text-[var(--text-primary)] font-semibold">最近会话</div>
      <router-link to="/projects" class="text-xs text-blue-400 hover:text-blue-300 transition-colors">
        查看全部 →
      </router-link>
    </div>
    <div v-if="sessions.length === 0" class="text-center text-[var(--text-secondary)] text-sm py-6">
      暂无会话
    </div>
    <div v-else class="flex flex-col gap-2">
      <button
        v-for="session in sessions"
        :key="session.session_id"
        @click="openSession(session)"
        class="w-full text-left bg-[var(--bg-page)] rounded-lg p-2.5 hover:bg-[var(--bg-assistant)] transition-colors group"
      >
        <div class="text-xs text-[var(--text-primary)] truncate group-hover:text-blue-400 transition-colors">
          {{ session.preview || 'No preview' }}
        </div>
        <div class="flex items-center gap-2 mt-1.5">
          <span class="text-[10px] text-[var(--text-secondary)] bg-[var(--bg-card)] px-1.5 py-0.5 rounded truncate max-w-[120px]">
            {{ session.project_path }}
          </span>
          <span class="text-[10px] text-[var(--text-secondary)]">{{ session.message_count }} msgs</span>
          <span class="text-[10px] text-[var(--text-secondary)] ml-auto">{{ formatTime(session.timestamp) }}</span>
        </div>
      </button>
    </div>
  </div>
</template>
