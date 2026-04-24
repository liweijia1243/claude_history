<script setup>
import { ref, onMounted, computed, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'
import 'highlight.js/styles/github-dark.css'
import hljs from 'highlight.js'
import ConversationMessage from '../components/ConversationMessage.vue'
import { stripAnsi, isTerminalOutput, processTerminalOutput } from '../utils/ansiToHtml.js'
import { apiPath, routePath, sourceFromRoute } from '../utils/source'
import { useLatestRequest } from '../composables/useLatestRequest'

// Custom renderer for code blocks
const renderer = new marked.Renderer()
renderer.code = function({ text, lang }) {
  const language = lang || ''
  const highlighted = language && hljs.getLanguage(language)
    ? hljs.highlight(text, { language }).value
    : hljs.highlightAuto(text).value
  return `<div class="code-block-wrapper"><div class="flex items-center justify-between px-4 py-2 bg-[#2d2d2d] border-b border-[#404040]"><span class="text-xs font-medium text-[#a0a0a0] uppercase tracking-wide">${language || 'code'}</span></div><pre class="!m-0 !rounded-b-xl !border-t-0"><code class="language-${language}">${highlighted}</code></pre></div>`
}
renderer.codespan = function({ text }) {
  const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  return `<code class="inline-code">${escaped}</code>`
}

marked.setOptions({
  renderer,
})

const props = defineProps({
  projectId: String,
  sessionId: String,
})

const route = useRoute()
const router = useRouter()
const source = computed(() => sourceFromRoute(route))
const conversation = ref([])
const subagents = ref([])
const sessionMetadata = ref({})
const loading = ref(true)
const fromHistory = computed(() => route.query.source === 'history')
const fromProject = computed(() => route.query.source === 'project')
const totalRaw = ref(0)
const showThinking = ref(localStorage.getItem('conv_showThinking') === 'true')
const showTools = ref(localStorage.getItem('conv_showTools') === 'true')
const showAgents = ref(localStorage.getItem('conv_showAgents') === 'true')
const conversationRequests = useLatestRequest()

watch(showThinking, v => localStorage.setItem('conv_showThinking', v))
watch(showTools, v => localStorage.setItem('conv_showTools', v))
watch(showAgents, v => localStorage.setItem('conv_showAgents', v))

const subagentShowTools = ref(localStorage.getItem('conv_subagentShowTools') !== 'false')

watch(subagentShowTools, v => localStorage.setItem('conv_subagentShowTools', v))

const selectedSubagent = ref(null)
const subagentConversation = ref([])
const subagentRequests = useLatestRequest()

async function fetchConversation() {
  const request = conversationRequests.createRequest({
    source: source.value,
    projectId: props.projectId,
    sessionId: props.sessionId,
  })
  const { source: requestSource, projectId: requestProjectId, sessionId: requestSessionId } = request.snapshot
  loading.value = true
  const isCurrent = () => request.isCurrent(
    snapshot => snapshot.source === source.value
      && snapshot.projectId === props.projectId
      && snapshot.sessionId === props.sessionId
  )
  try {
    const res = await fetch(apiPath(requestSource, `/projects/${requestProjectId}/sessions/${requestSessionId}`))
    if (!isCurrent()) return

    if (!res.ok) {
      router.push(routePath(requestSource, '/projects'))
      return
    }

    const data = await res.json()
    if (!isCurrent()) return

    conversation.value = data.conversation
    subagents.value = data.subagents || []
    sessionMetadata.value = data.metadata || {}
    totalRaw.value = data.total_raw_messages
    loading.value = false
    scrollToMessage()
  } catch {
    if (isCurrent()) {
      router.push(routePath(requestSource, '/projects'))
    }
  } finally {
    if (isCurrent()) {
      loading.value = false
    }
  }
}

onMounted(async () => {
  await fetchConversation()
})

function formatTime(ts) {
  if (!ts) return ''
  const d = typeof ts === 'number' ? new Date(ts) : new Date(ts)
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function renderMarkdown(text) {
  if (!text) return ''

  // Check if this looks like terminal output with visual formatting
  if (isTerminalOutput(text)) {
    return processTerminalOutput(text)
  }

  // Normal markdown processing
  const cleanText = stripAnsi(text)
  return marked.parse(cleanText)
}

function getModelShort(model) {
  if (!model) return ''
  if (model.includes('sonnet')) return 'Sonnet'
  if (model.includes('opus')) return 'Opus'
  if (model.includes('haiku')) return 'Haiku'
  if (model.includes('deepseek')) return 'DeepSeek'
  return model.split('-').slice(0, 2).join('-')
}

function getModelIcon(model) {
  if (!model) return '🤖'
  if (model.includes('opus')) return '🟣'
  if (model.includes('sonnet')) return '🔵'
  if (model.includes('haiku')) return '🟢'
  return '🤖'
}

async function openSubagent(agent) {
  const request = subagentRequests.createRequest({
    source: source.value,
    projectId: props.projectId,
    sessionId: props.sessionId,
  })
  const { source: requestSource, projectId: requestProjectId, sessionId: requestSessionId } = request.snapshot
  const isCurrent = () => request.isCurrent(
    snapshot => snapshot.source === source.value
      && snapshot.projectId === props.projectId
      && snapshot.sessionId === props.sessionId
  )
  try {
    const res = await fetch(
      apiPath(requestSource, `/projects/${requestProjectId}/sessions/${requestSessionId}/subagents/${agent.filename}`)
    )
    if (!res.ok || !isCurrent()) return
    const data = await res.json()
    if (!isCurrent()) return
    subagentConversation.value = data.conversation
    selectedSubagent.value = agent
  } catch {
    // Keep the current conversation visible if a subagent panel cannot be loaded.
  }
}

function closeSubagent() {
  selectedSubagent.value = null
  subagentConversation.value = []
}

function handleAgentClick(tool) {
  const agentId = tool.metadata?.agent_id || tool.input?.agent_id || tool.input?.target
  if (agentId) {
    const agent = subagents.value.find(s => s.id === agentId || s.session_id === agentId || s.filename === agentId)
    if (agent) {
      openSubagent(agent)
      return true
    }
  }

  const input = tool.input || {}
  const subagentType = input.subagent_type || 'general-purpose'
  const agent = subagents.value.find(
    s => s.type === subagentType && s.description === input.description
  )
  if (agent) {
    openSubagent(agent)
    return true
  }
  return false
}

function goBack() {
  router.push(routePath(source.value, `/projects/${props.projectId}`))
}

async function scrollToMessage() {
  const msgTimestamp = route.query.msgTimestamp
  if (!msgTimestamp) return

  await nextTick()
  setTimeout(() => {
    const targetMs = Number(msgTimestamp)
    const messages = document.querySelectorAll('[data-msg-timestamp]')

    // First pass: try exact timestamp match (within 1 second)
    for (const el of messages) {
      const raw = el.dataset.msgTimestamp
      const elMs = new Date(raw).getTime()
      if (Math.abs(elMs - targetMs) < 1000) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        return
      }
    }

    // Second pass: for local commands like /context, the output is embedded
    // in a subsequent user message. Try to find a message with terminal output
    // (contains Context Usage or similar patterns) within 5 minutes
    const fiveMinutes = 5 * 60 * 1000
    for (const el of messages) {
      const raw = el.dataset.msgTimestamp
      const elMs = new Date(raw).getTime()
      if (elMs > targetMs && elMs - targetMs < fiveMinutes) {
        // Check if this message contains terminal output (from /context, etc.)
        if (el.innerHTML.includes('Context Usage') ||
            el.querySelector('.terminal-output')) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' })
          return
        }
      }
    }
  }, 100)
}

function goBackToHistory() {
  const query = route.query.q ? { q: route.query.q } : {}
  router.push({ path: routePath(source.value, '/history'), query })
}

function goBackToProject() {
  const query = route.query.q ? { q: route.query.q } : {}
  router.push({ path: routePath(source.value, `/projects/${props.projectId}`), query })
}

const sessionModel = computed(() => sessionMetadata.value?.model || '')
const sessionReasoningEffort = computed(() => sessionMetadata.value?.reasoning_effort || '')

watch([source, () => props.projectId, () => props.sessionId], () => {
  subagentRequests.cancelRequests()
  selectedSubagent.value = null
  subagentConversation.value = []
  fetchConversation()
})
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
      <button
        v-if="fromHistory"
        @click="goBackToHistory"
        class="flex items-center gap-1.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors text-sm"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
        History
      </button>
      <button
        v-if="fromProject"
        @click="goBackToProject"
        class="flex items-center gap-1.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors text-sm"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>
        Project
      </button>
      <div class="flex-1 min-w-0">
        <span class="text-sm text-[var(--text-secondary)] font-mono">{{ sessionId }}</span>
        <span class="text-xs text-[var(--text-secondary)] opacity-50 ml-3">{{ totalRaw }} raw messages</span>
        <span v-if="sessionModel" class="text-xs text-[var(--text-secondary)] ml-3">
          {{ getModelShort(sessionModel) }}
        </span>
        <span v-if="sessionReasoningEffort" class="text-xs text-[var(--text-secondary)] ml-2">
          reasoning: {{ sessionReasoningEffort }}
        </span>
      </div>
      <label class="flex items-center gap-2 text-xs text-[var(--text-secondary)] cursor-pointer hover:text-[var(--text-primary)] transition-colors">
        <input type="checkbox" v-model="showThinking" class="rounded border-[var(--border-color)] accent-purple-500" />
        Show Thinking
      </label>
      <label class="flex items-center gap-2 text-xs text-[var(--text-secondary)] cursor-pointer hover:text-[var(--text-primary)] transition-colors">
        <input type="checkbox" v-model="showTools" class="rounded border-[var(--border-color)] accent-emerald-500" />
        Show Tools
      </label>
      <label class="flex items-center gap-2 text-xs text-[var(--text-secondary)] cursor-pointer hover:text-[var(--text-primary)] transition-colors">
        <input type="checkbox" v-model="showAgents" class="rounded border-[var(--border-color)] accent-orange-500" />
        Show Agents
      </label>
    </div>

    <!-- Subagent Panel (overlay) -->
    <Transition name="fade">
      <div
        v-if="selectedSubagent"
        class="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-8"
        @click.self="closeSubagent"
      >
        <div class="bg-[var(--bg-card)] rounded-2xl border border-[var(--border-color)] w-full max-w-4xl max-h-[85vh] overflow-auto shadow-2xl">
          <div class="sticky top-0 bg-[var(--bg-card)] border-b border-[var(--border-color)] px-6 py-4 flex items-center justify-between">
            <div>
              <span class="text-sm font-semibold text-[var(--text-primary)]">Subagent: {{ selectedSubagent.type }}</span>
              <span class="text-xs text-[var(--text-secondary)] ml-2 font-mono">{{ selectedSubagent.filename }}</span>
            </div>
            <div class="flex items-center gap-4">
              <label class="flex items-center gap-2 text-xs text-[var(--text-secondary)] cursor-pointer hover:text-[var(--text-primary)] transition-colors">
                <input type="checkbox" v-model="subagentShowTools" class="rounded border-[var(--border-color)] accent-emerald-500" />
                Show Tools
              </label>
              <button @click="closeSubagent" class="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
              </button>
            </div>
          </div>
          <div class="p-6 space-y-4">
            <ConversationMessage
              v-for="(msg, i) in subagentConversation"
              :key="i"
              :msg="msg"
              variant="subagent"
              :show-thinking="showThinking"
              :show-tools="subagentShowTools"
              :render-markdown="renderMarkdown"
            />
          </div>
        </div>
      </div>
    </Transition>

    <!-- Conversation -->
    <div class="flex-1 overflow-auto">
      <div v-if="loading" class="text-[var(--text-secondary)] text-center py-16">Loading conversation...</div>

      <div v-else class="max-w-4xl mx-auto py-8 space-y-6 px-6">
        <div
          v-for="(msg, i) in conversation"
          :key="i"
          class="group"
        >
          <ConversationMessage
            :msg="msg"
            :show-thinking="showThinking"
            :show-tools="showTools"
            :show-agents="showAgents"
            :render-markdown="renderMarkdown"
            :get-model-icon="getModelIcon"
            :get-model-short="getModelShort"
            :open-subagent-handler="handleAgentClick"
          />
        </div>

        <!-- Subagents -->
        <div v-if="subagents.length > 0" class="mt-8 pt-6 border-t border-[var(--border-color)]">
          <h3 class="text-sm font-semibold text-[var(--text-secondary)] mb-4 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
            Subagents ({{ subagents.length }})
          </h3>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="agent in subagents"
              :key="agent.filename"
              @click="openSubagent(agent)"
              class="inline-flex items-center gap-2 bg-[var(--bg-card)] hover:bg-[var(--bg-assistant)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] transition-colors"
            >
              <span class="text-purple-400">◈</span>
              {{ agent.type }}
              <span class="text-xs text-[var(--text-secondary)]">{{ (agent.size / 1024).toFixed(0) }}KB</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

</style>
