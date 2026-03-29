<script setup>
import { ref } from 'vue'
import CodeBlock from './CodeBlock.vue'
import DiffBlock from './DiffBlock.vue'

const props = defineProps({
  toolUses: Array,
  toolResults: Array,
})

const expanded = ref({})

function toggle(idx) {
  expanded.value[idx] = !expanded.value[idx]
}

function isExpanded(idx) {
  return expanded.value[idx] || false
}

function toolResultFor(useId) {
  return props.toolResults?.find(r => r.tool_use_id === useId)
}

function resultPreview(result) {
  if (!result?.content) return ''
  const c = result.content
  if (c.length > 800) return c.substring(0, 800) + '...'
  return c
}

const toolConfig = {
  Bash: {
    color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/></svg>`,
    label: (inp) => `$ ${inp.command || ''}`
  },
  Read: {
    color: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14,2 14,8 20,8"/></svg>`,
    label: (inp) => inp.file_path || ''
  },
  Write: {
    color: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>`,
    label: (inp) => inp.file_path || ''
  },
  Edit: {
    color: 'text-orange-400 bg-orange-500/10 border-orange-500/20',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>`,
    label: (inp) => inp.file_path || ''
  },
  Glob: {
    color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>`,
    label: (inp) => inp.pattern || ''
  },
  Grep: {
    color: 'text-teal-400 bg-teal-500/10 border-teal-500/20',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><text x="0" y="15" font-size="12" font-weight="bold" fill="currentColor">Aa</text></svg>`,
    label: (inp) => inp.pattern || ''
  },
  Agent: {
    color: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>`,
    label: (inp) => inp.description || inp.subagent_type || ''
  },
  TaskOutput: {
    color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>`,
    label: (inp) => inp.task_id?.substring(0, 12) || ''
  },
  AskUserQuestion: {
    color: 'text-pink-400 bg-pink-500/10 border-pink-500/20',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/></svg>`,
    label: (inp) => inp.questions?.[0]?.question?.substring(0, 50) || ''
  },
  WebSearch: {
    color: 'text-sky-400 bg-sky-500/10 border-sky-500/20',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" x2="22" y1="12" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>`,
    label: (inp) => inp.query?.substring(0, 50) || ''
  },
}

function getToolConfig(name) {
  return toolConfig[name] || {
    color: 'text-gray-400 bg-gray-500/10 border-gray-500/20',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/></svg>`,
    label: () => name
  }
}

function formatLabel(tool) {
  const config = getToolConfig(tool.name)
  return config.label(tool.input || {})
}
</script>

<template>
  <div class="mt-3 space-y-2">
    <div v-for="(tool, i) in toolUses" :key="tool.id || i">
      <!-- Collapsed header -->
      <button
        @click="toggle(i)"
        :class="getToolConfig(tool.name).color"
        class="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg border text-sm font-mono transition-all hover:opacity-80"
      >
        <svg
          :class="[isExpanded(i) ? 'rotate-90' : '']"
          xmlns="http://www.w3.org/2000/svg"
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="transition-transform flex-shrink-0"
        >
          <path d="m9 18 6-6-6-6"/>
        </svg>
        <span class="flex-shrink-0 opacity-80" v-html="getToolConfig(tool.name).icon"></span>
        <span class="font-medium">{{ tool.name }}</span>
        <span class="text-[var(--text-secondary)] truncate">{{ formatLabel(tool) }}</span>
      </button>

      <!-- Expanded content -->
      <Transition name="expand">
        <div v-if="isExpanded(i)" class="mt-1.5 ml-4 pl-3 border-l-2 border-[var(--border-color)] space-y-2">
          <!-- Edit tool - show diff view -->
          <DiffBlock
            v-if="tool.name === 'Edit'"
            :old-string="tool.input?.old_string || ''"
            :new-string="tool.input?.new_string || ''"
            :file-path="tool.input?.file_path || ''"
            :start-line="tool.startLine"
            :structured-patch="tool.structuredPatch"
          />

          <!-- Write tool - show code block -->
          <div v-else-if="tool.name === 'Write' && tool.input?.content" class="rounded-xl overflow-hidden border border-[var(--border-color)]">
            <CodeBlock :code="tool.input.content" :language="tool.input?.file_path?.split('.').pop() || 'text'" />
          </div>

          <!-- Read tool - show result if available, otherwise show file path -->
          <div v-else-if="tool.name === 'Read'" class="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-3">
            <div class="text-xs font-semibold text-[var(--text-secondary)] mb-2 flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/></svg>
              {{ tool.input?.file_path || 'file' }}
            </div>
          </div>

          <!-- Other tools - show JSON input -->
          <div v-else class="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-3">
            <div class="text-xs font-semibold text-[var(--text-secondary)] mb-2 uppercase tracking-wide">Input</div>
            <pre class="text-xs text-[var(--text-primary)] whitespace-pre-wrap break-words max-h-64 overflow-auto">{{ JSON.stringify(tool.input, null, 2) }}</pre>
          </div>

          <!-- Tool Result -->
          <div v-if="toolResultFor(tool.id)" class="rounded-xl overflow-hidden border border-[var(--border-color)]">
            <!-- Bash result with terminal style -->
            <div v-if="tool.name === 'Bash'" class="terminal-output">
              <div class="text-xs text-emerald-400/60 mb-1">$ {{ tool.input?.command }}</div>
              <pre class="whitespace-pre-wrap break-words max-h-80 overflow-auto">{{ resultPreview(toolResultFor(tool.id)) }}</pre>
            </div>
            <!-- Read result - show as code block -->
            <CodeBlock
              v-else-if="tool.name === 'Read'"
              :code="resultPreview(toolResultFor(tool.id))"
              :language="tool.input?.file_path?.split('.').pop() || 'text'"
            />
            <!-- Regular result -->
            <div v-else class="bg-[var(--bg-card)] p-3">
              <div class="text-xs font-semibold mb-2 uppercase tracking-wide flex items-center gap-2">
                <span class="text-[var(--text-secondary)]">Result</span>
                <span v-if="toolResultFor(tool.id).is_error" class="text-red-400 text-[10px] px-1.5 py-0.5 bg-red-500/10 rounded">ERROR</span>
              </div>
              <pre class="text-xs text-[var(--text-primary)] whitespace-pre-wrap break-words max-h-96 overflow-auto">{{ resultPreview(toolResultFor(tool.id)) }}</pre>
            </div>
          </div>
        </div>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.expand-enter-active,
.expand-leave-active {
  transition: all 0.2s ease-out;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}

.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 2000px;
}

/* Terminal output styling */
.terminal-output {
  background-color: #1e1e1e;
  color: #d4d4d4;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.8125rem;
  line-height: 1.5;
  padding: 0.75rem 1rem;
  overflow-x: auto;
}

.terminal-output pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  color: #d4d4d4;
}

/* JSON input/result display */
pre {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
</style>
