<script setup>
import { computed, onMounted, ref } from 'vue'
import hljs from 'highlight.js'
import hljsDefineVue from '../utils/hljsVue.js'

// Register Vue language support
hljs.registerLanguage('vue', hljsDefineVue)

const props = defineProps({
  oldString: {
    type: String,
    default: ''
  },
  newString: {
    type: String,
    default: ''
  },
  filePath: {
    type: String,
    default: ''
  },
  startLine: {
    type: Number,
    default: null
  }
})

// Detect language from file path
const language = computed(() => {
  if (!props.filePath) return null
  const ext = props.filePath.split('.').pop()?.toLowerCase()
  const langMap = {
    'js': 'javascript',
    'ts': 'typescript',
    'vue': 'vue',
    'py': 'python',
    'md': 'markdown',
    'json': 'json',
    'css': 'css',
    'html': 'html',
    'sh': 'bash',
    'bash': 'bash',
    'yaml': 'yaml',
    'yml': 'yaml',
    'toml': 'toml',
    'rs': 'rust',
    'go': 'go',
    'java': 'java',
    'cpp': 'cpp',
    'c': 'c',
    'h': 'c',
  }
  return langMap[ext] || ext
})

// Simple diff algorithm - compute unified diff-style output
const diffLines = computed(() => {
  const oldLines = props.oldString ? props.oldString.split('\n') : []
  const newLines = props.newString ? props.newString.split('\n') : []

  // Simple LCS-based diff
  const result = []

  // Find common prefix and suffix
  let prefixLen = 0
  while (prefixLen < oldLines.length && prefixLen < newLines.length && oldLines[prefixLen] === newLines[prefixLen]) {
    prefixLen++
  }

  let suffixLen = 0
  while (
    suffixLen < oldLines.length - prefixLen &&
    suffixLen < newLines.length - prefixLen &&
    oldLines[oldLines.length - 1 - suffixLen] === newLines[newLines.length - 1 - suffixLen]
  ) {
    suffixLen++
  }

  // Calculate base line numbers
  const baseOldLine = props.startLine ?? 1
  const baseNewLine = props.startLine ?? 1

  // Add common prefix (context)
  for (let i = 0; i < prefixLen; i++) {
    result.push({
      type: 'context',
      content: oldLines[i],
      oldLine: baseOldLine + i,
      newLine: baseNewLine + i
    })
  }

  // Add removed lines
  const removedStart = prefixLen
  const removedEnd = oldLines.length - suffixLen
  for (let i = removedStart; i < removedEnd; i++) {
    result.push({
      type: 'remove',
      content: oldLines[i],
      oldLine: baseOldLine + i,
      newLine: null
    })
  }

  // Add added lines
  const addedStart = prefixLen
  const addedEnd = newLines.length - suffixLen
  for (let i = addedStart; i < addedEnd; i++) {
    result.push({
      type: 'add',
      content: newLines[i],
      oldLine: null,
      newLine: baseNewLine + i
    })
  }

  // Add common suffix (context)
  for (let i = 0; i < suffixLen; i++) {
    const oldIdx = oldLines.length - suffixLen + i
    const newIdx = newLines.length - suffixLen + i
    result.push({
      type: 'context',
      content: oldLines[oldIdx],
      oldLine: baseOldLine + oldIdx,
      newLine: baseNewLine + newIdx
    })
  }

  return result
})

const stats = computed(() => {
  const added = diffLines.value.filter(l => l.type === 'add').length
  const removed = diffLines.value.filter(l => l.type === 'remove').length
  return { added, removed }
})

// Syntax highlighting for each line
const highlightedLines = ref({})

onMounted(() => {
  if (language.value && hljs.getLanguage(language.value)) {
    // Highlight the full old and new strings, then split
    try {
      const oldHighlighted = hljs.highlight(props.oldString, { language: language.value }).value
      const newHighlighted = hljs.highlight(props.newString, { language: language.value }).value

      const oldLinesHl = oldHighlighted.split('\n')
      const newLinesHl = newHighlighted.split('\n')

      // Map content to highlighted content
      const oldLinesRaw = props.oldString.split('\n')
      const newLinesRaw = props.newString.split('\n')

      oldLinesRaw.forEach((line, i) => {
        if (oldLinesHl[i]) {
          highlightedLines.value[line] = oldLinesHl[i]
        }
      })
      newLinesRaw.forEach((line, i) => {
        if (newLinesHl[i]) {
          highlightedLines.value[line] = newLinesHl[i]
        }
      })
    } catch (e) {
      // Fallback to no highlighting
    }
  }
})

function getHighlightedContent(line) {
  return highlightedLines.value[line] || escapeHtml(line)
}

function escapeHtml(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}
</script>

<template>
  <div class="diff-block mt-3 mb-3 rounded-xl overflow-hidden border border-[var(--border-color)]">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-2.5 bg-[#1f2937] border-b border-[#374151]">
      <div class="flex items-center gap-3">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
        <span class="text-xs text-[#f97316] font-medium">Edit</span>
        <span v-if="filePath" class="text-xs text-[#9ca3af] font-mono truncate max-w-[300px]">{{ filePath }}</span>
      </div>
      <div class="flex items-center gap-2 text-xs font-medium">
        <span v-if="stats.removed > 0" class="px-1.5 py-0.5 rounded bg-[#f87171]/20 text-[#f87171]">-{{ stats.removed }}</span>
        <span v-if="stats.added > 0" class="px-1.5 py-0.5 rounded bg-[#4ade80]/20 text-[#4ade80]">+{{ stats.added }}</span>
      </div>
    </div>

    <!-- Diff content -->
    <div class="overflow-x-auto">
      <table class="w-full font-mono text-[13px] leading-[1.5]">
        <tbody>
          <tr
            v-for="(line, i) in diffLines"
            :key="i"
            :class="[
              line.type === 'remove' ? 'bg-[#f87171]/10' : '',
              line.type === 'add' ? 'bg-[#4ade80]/10' : ''
            ]"
          >
            <!-- Old line number -->
            <td
              :class="[
                'w-10 px-2 text-right select-none border-r',
                line.type === 'remove' ? 'text-[#f87171]/50 bg-[#f87171]/5' : '',
                line.type === 'add' ? 'text-transparent border-[#374151]' : 'text-[#6b7280] border-[#374151]',
                line.type === 'context' ? 'text-[#6b7280] border-[#374151]' : ''
              ]"
            >
              {{ line.oldLine ?? '' }}
            </td>
            <!-- New line number -->
            <td
              :class="[
                'w-10 px-2 text-right select-none border-r',
                line.type === 'add' ? 'text-[#4ade80]/50 bg-[#4ade80]/5' : '',
                line.type === 'remove' ? 'text-transparent border-[#374151]' : 'text-[#6b7280] border-[#374151]',
                line.type === 'context' ? 'text-[#6b7280] border-[#374151]' : ''
              ]"
            >
              {{ line.newLine ?? '' }}
            </td>
            <!-- +/- sign -->
            <td
              :class="[
                'w-6 text-center select-none',
                line.type === 'remove' ? 'text-[#f87171] bg-[#f87171]/10' : '',
                line.type === 'add' ? 'text-[#4ade80] bg-[#4ade80]/10' : 'text-[#4b5563]'
              ]"
            >
              {{ line.type === 'remove' ? '-' : line.type === 'add' ? '+' : ' ' }}
            </td>
            <!-- Content with syntax highlighting -->
            <td
              :class="[
                'px-3 whitespace-pre',
                line.type === 'remove' ? 'text-[#fca5a5]' : '',
                line.type === 'add' ? 'text-[#86efac]' : 'text-[#d1d5db]'
              ]"
              v-html="getHighlightedContent(line.content)"
            ></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.diff-block {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
}

table {
  border-collapse: collapse;
  background-color: #111827;
}

td {
  vertical-align: top;
  border: none;
}

/* Syntax highlighting colors - override for diff context */
.diff-block :deep(.hljs-keyword) { color: #569cd6; }
.diff-block :deep(.hljs-string) { color: #ce9178; }
.diff-block :deep(.hljs-number) { color: #b5cea8; }
.diff-block :deep(.hljs-function) { color: #dcdcaa; }
.diff-block :deep(.hljs-variable) { color: #9cdcfe; }
.diff-block :deep(.hljs-comment) { color: #6a9955; }
</style>
