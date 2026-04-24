<script setup>
import ToolCallBlock from './ToolCallBlock.vue'
import ThinkingBlock from './ThinkingBlock.vue'

const props = defineProps({
  msg: { type: Object, required: true },
  variant: { type: String, default: 'main' },
  showThinking: { type: Boolean, default: false },
  showTools: { type: Boolean, default: false },
  showAgents: { type: Boolean, default: false },
  renderMarkdown: { type: Function, required: true },
  getModelIcon: { type: Function, default: () => '' },
  getModelShort: { type: Function, default: model => model || '' },
  openSubagentHandler: Function,
})

const agentToolNames = new Set(['Agent', 'TaskOutput', 'spawn_agent', 'wait_agent', 'send_input', 'close_agent', 'resume_agent'])

function getAgentTools(toolUses) {
  return toolUses?.filter(t => agentToolNames.has(t.name)) || []
}

function getNonAgentTools(toolUses) {
  return toolUses?.filter(t => !agentToolNames.has(t.name)) || []
}

function hasVisibleMainContent(msg) {
  return msg.content
    || (props.showThinking && msg.thinking)
    || (props.showTools && getNonAgentTools(msg.tool_uses).length)
    || (props.showAgents && getAgentTools(msg.tool_uses).length)
}
</script>

<template>
  <div
    v-if="variant === 'subagent'"
    :class="[
      'rounded-xl p-4',
      msg.role === 'user' ? 'bg-[var(--bg-card)] ml-8' : 'bg-[var(--bg-assistant)] mr-8'
    ]"
  >
    <div
      v-if="msg.role === 'user' || msg.content || (showThinking && msg.thinking) || (showTools && msg.tool_uses?.length)"
      class="text-xs text-[var(--text-secondary)] mb-2 font-semibold uppercase tracking-wide"
    >
      {{ msg.role === 'user' ? 'User' : 'Assistant' }}
    </div>
    <div
      v-if="msg.content"
      class="prose prose-sm max-w-none"
      v-html="renderMarkdown(msg.content)"
    ></div>
    <ThinkingBlock v-if="showThinking && msg.thinking" :thinking="msg.thinking" />
    <ToolCallBlock v-if="showTools && msg.tool_uses?.length" :tool-uses="msg.tool_uses" :tool-results="msg.tool_results" />
  </div>

  <div v-else-if="msg.role === 'user'" class="flex justify-end" :data-msg-timestamp="msg.timestamp">
    <div class="user-bubble rounded-2xl rounded-br-sm px-5 py-3 max-w-[85%]">
      <div
        class="prose prose-sm max-w-none prose-p:m-0"
        v-html="renderMarkdown(msg.content)"
      ></div>
    </div>
  </div>

  <div v-else-if="msg.role === 'assistant'" class="w-full">
    <div v-if="msg.model && hasVisibleMainContent(msg)" class="flex items-center gap-2 mb-3">
      <span class="text-sm">{{ getModelIcon(msg.model) }}</span>
      <span class="text-sm font-medium text-[var(--text-primary)]">{{ getModelShort(msg.model) }}</span>
      <span v-if="msg.usage" class="text-xs text-[var(--text-secondary)] bg-[var(--bg-card)] px-2 py-0.5 rounded-full">
        {{ msg.usage.input_tokens }}in / {{ msg.usage.output_tokens }}out
      </span>
    </div>

    <ThinkingBlock
      v-if="showThinking && msg.thinking"
      :thinking="msg.thinking"
    />

    <div
      v-if="msg.content"
      class="prose prose-sm max-w-none"
      v-html="renderMarkdown(msg.content)"
    ></div>

    <ToolCallBlock
      v-if="showTools && getNonAgentTools(msg.tool_uses).length"
      :tool-uses="getNonAgentTools(msg.tool_uses)"
      :tool-results="msg.tool_results"
    />

    <ToolCallBlock
      v-if="showAgents && getAgentTools(msg.tool_uses).length"
      :tool-uses="getAgentTools(msg.tool_uses)"
      :tool-results="msg.tool_results"
      :open-subagent-handler="openSubagentHandler"
    />
  </div>

  <div v-else class="flex justify-center" :data-msg-timestamp="msg.timestamp">
    <div class="max-w-[85%] rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] px-3 py-2 text-xs text-[var(--text-secondary)]">
      <div v-if="msg.metadata?.phase" class="mb-1 font-semibold uppercase tracking-wide">
        {{ msg.metadata.phase }}
      </div>
      <div
        v-if="msg.content"
        class="prose prose-sm max-w-none"
        v-html="renderMarkdown(msg.content)"
      ></div>
    </div>
  </div>
</template>

<style scoped>
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
