<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'
import 'highlight.js/styles/github-dark.css'
import hljs from 'highlight.js'
import ToolCallBlock from '../components/ToolCallBlock.vue'
import ThinkingBlock from '../components/ThinkingBlock.vue'
import CodeBlock from '../components/CodeBlock.vue'
import { stripAnsi, isTerminalOutput, processTerminalOutput } from '../utils/ansiToHtml.js'

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
const conversation = ref([])
const subagents = ref([])
const loading = ref(true)
const fromHistory = computed(() => route.query.source === 'history')
const fromProject = computed(() => route.query.source === 'project')
const totalRaw = ref(0)
const showThinking = ref(false)
const showTools = ref(false)
const showAgents = ref(false)

const agentToolNames = new Set(['Agent', 'TaskOutput'])

function getAgentTools(toolUses) {
  return toolUses?.filter(t => agentToolNames.has(t.name)) || []
}

function getNonAgentTools(toolUses) {
  return toolUses?.filter(t => !agentToolNames.has(t.name)) || []
}

const subagentShowTools = ref(true)

const selectedSubagent = ref(null)
const subagentConversation = ref([])

onMounted(async () => {
  const res = await fetch(`/api/projects/${props.projectId}/sessions/${props.sessionId}`)
  const data = await res.json()
  conversation.value = data.conversation
  subagents.value = data.subagents || []
  totalRaw.value = data.total_raw_messages
  loading.value = false
  scrollToMessage()
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
  const res = await fetch(
    `/api/projects/${props.projectId}/sessions/${props.sessionId}/subagents/${agent.filename}`
  )
  const data = await res.json()
  subagentConversation.value = data.conversation
  selectedSubagent.value = agent
}

function closeSubagent() {
  selectedSubagent.value = null
  subagentConversation.value = []
}

function handleAgentClick(tool) {
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
  router.push(`/projects/${props.projectId}`)
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
  router.push({ path: '/history', query })
}

function goBackToProject() {
  const query = route.query.q ? { q: route.query.q } : {}
  router.push({ path: `/projects/${props.projectId}`, query })
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
        <span class="text-sm text-[var(--text-secondary)] font-mono">{{ sessionId?.substring(0, 16) }}...</span>
        <span class="text-xs text-[var(--text-secondary)] opacity-50 ml-3">{{ totalRaw }} raw messages</span>
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
            <div
              v-for="(msg, i) in subagentConversation"
              :key="i"
              :class="[
                'rounded-xl p-4',
                msg.role === 'user' ? 'bg-[var(--bg-card)] ml-8' : 'bg-[var(--bg-assistant)] mr-8'
              ]"
            >
              <div v-if="msg.role === 'user' || msg.content || (showThinking && msg.thinking) || (subagentShowTools && msg.tool_uses?.length)" class="text-xs text-[var(--text-secondary)] mb-2 font-semibold uppercase tracking-wide">
                {{ msg.role === 'user' ? 'User' : 'Assistant' }}
              </div>
              <div
                v-if="msg.content"
                class="prose prose-sm max-w-none"
                v-html="renderMarkdown(msg.content)"
              ></div>
              <ThinkingBlock v-if="showThinking && msg.thinking" :thinking="msg.thinking" />
              <ToolCallBlock v-if="subagentShowTools && msg.tool_uses?.length" :tool-uses="msg.tool_uses" :tool-results="msg.tool_results" />
            </div>
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
          <!-- User Message -->
          <div v-if="msg.role === 'user'" class="flex justify-end" :data-msg-timestamp="msg.timestamp">
            <div class="user-bubble rounded-2xl rounded-br-sm px-5 py-3 max-w-[85%]">
              <div
                class="prose prose-sm max-w-none prose-p:m-0"
                v-html="renderMarkdown(msg.content)"
              ></div>
            </div>
          </div>

          <!-- Assistant Message -->
          <div v-else class="w-full">
            <!-- Model header -->
            <div v-if="msg.model && (msg.content || (showThinking && msg.thinking) || (showTools && getNonAgentTools(msg.tool_uses).length) || (showAgents && getAgentTools(msg.tool_uses).length))" class="flex items-center gap-2 mb-3">
              <span class="text-sm">{{ getModelIcon(msg.model) }}</span>
              <span class="text-sm font-medium text-[var(--text-primary)]">{{ getModelShort(msg.model) }}</span>
              <span v-if="msg.usage" class="text-xs text-[var(--text-secondary)] bg-[var(--bg-card)] px-2 py-0.5 rounded-full">
                {{ msg.usage.input_tokens }}in / {{ msg.usage.output_tokens }}out
              </span>
            </div>

            <!-- Thinking -->
            <ThinkingBlock
              v-if="showThinking && msg.thinking"
              :thinking="msg.thinking"
            />

            <!-- Content - ChatGPT style, no background -->
            <div
              v-if="msg.content"
              class="prose prose-sm max-w-none"
              v-html="renderMarkdown(msg.content)"
            ></div>

            <!-- Non-Agent Tool Uses -->
            <ToolCallBlock
              v-if="showTools && getNonAgentTools(msg.tool_uses).length"
              :tool-uses="getNonAgentTools(msg.tool_uses)"
              :tool-results="msg.tool_results"
            />

            <!-- Agent Tool Uses -->
            <ToolCallBlock
              v-if="showAgents && getAgentTools(msg.tool_uses).length"
              :tool-uses="getAgentTools(msg.tool_uses)"
              :tool-results="msg.tool_results"
              :open-subagent-handler="handleAgentClick"
            />
          </div>
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

/* User bubble - responds to theme */
.user-bubble {
  background-color: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1e40af;
  overflow: hidden;
}

.dark .user-bubble {
  background-color: #1e3a5f;
  border: 1px solid #2d4a6f;
  color: #bfdbfe;
}

.user-bubble .prose {
  --tw-prose-body: #1e40af;
  --tw-prose-headings: #1e40af;
  --tw-prose-links: #1d4ed8;
  overflow-wrap: break-word;
}

.user-bubble pre {
  max-width: 100%;
  min-width: 0;
  overflow-x: auto;
}

.dark .user-bubble .prose {
  --tw-prose-body: #bfdbfe;
  --tw-prose-headings: #bfdbfe;
  --tw-prose-links: #93c5fd;
}

.user-bubble :deep(code:not(pre code)) {
  background-color: rgba(59, 130, 246, 0.15);
  color: #1d4ed8;
}

.dark .user-bubble :deep(code:not(pre code)) {
  background-color: rgba(59, 130, 246, 0.25);
  color: #93c5fd;
}

/* Code block wrapper styling */
:deep(.code-block-wrapper) {
  margin-top: 1rem;
  margin-bottom: 1rem;
  border-radius: 0.75rem;
  overflow: hidden;
  border: 1px solid var(--border-color);
  background-color: #1e1e1e;
}

:deep(.code-block-wrapper pre) {
  margin: 0 !important;
  background-color: #1e1e1e !important;
  padding: 1rem !important;
  border: none !important;
  border-radius: 0 !important;
}

:deep(.code-block-wrapper code) {
  font-size: 0.875rem;
  line-height: 1.625;
  color: #d4d4d4;
}

/* Prose pre styling - always dark background */
.prose :deep(pre) {
  background-color: #1e1e1e !important;
  border-radius: 0.75rem !important;
  border: 1px solid var(--border-color) !important;
  margin-top: 1rem !important;
  margin-bottom: 1rem !important;
  padding: 1rem !important;
}

.prose :deep(pre code) {
  background: transparent !important;
  color: #d4d4d4 !important;
  font-size: 0.875rem !important;
}

/* Inline code - using class from custom renderer */
:deep(.inline-code) {
  background-color: var(--bg-card);
  color: #9333ea;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
}

.dark :deep(.inline-code) {
  color: #f0abfc;
}

/* Fallback for prose inline code */
.prose :deep(code:not(pre code)) {
  background-color: var(--bg-card);
  color: #9333ea;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
}

.dark .prose :deep(code:not(pre code)) {
  color: #f0abfc;
}

/* Terminal output styling */
:deep(.terminal-output) {
  font-family: 'Fira Code', 'JetBrains Mono', 'SF Mono', 'Monaco', 'Menlo', 'Consolas', 'Liberation Mono', monospace;
  font-size: 0.8125rem;
  line-height: 1.4;
  background-color: #1a1a1a;
  color: #d4d4d4;
  padding: 1rem;
  margin: 0.75rem 0;
  border-radius: 0.75rem;
  border: 1px solid var(--border-color);
  overflow-x: auto;
  white-space: pre;
}

.dark :deep(.terminal-output) {
  background-color: #0d0d0d;
}
</style>
