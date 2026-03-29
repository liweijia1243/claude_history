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
  },
  structuredPatch: {
    type: Array,
    default: null
  }
})

const CONTEXT_LINES = 3

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

// Build diff lines from structuredPatch (preferred)
function buildFromStructuredPatch(patches) {
  const result = []

  for (let patchIdx = 0; patchIdx < patches.length; patchIdx++) {
    const patch = patches[patchIdx]
    const { oldStart, newStart, lines } = patch

    let oldLineNum = oldStart
    let newLineNum = newStart

    for (const line of lines) {
      const prefix = line[0]  // ' ', '-', '+'
      const content = line.slice(1)

      if (prefix === ' ') {
        // Context line
        result.push({
          type: 'context',
          content: content,
          oldLine: oldLineNum,
          newLine: newLineNum
        })
        oldLineNum++
        newLineNum++
      } else if (prefix === '-') {
        // Removed line
        result.push({
          type: 'remove',
          content: content,
          oldLine: oldLineNum,
          newLine: null
        })
        oldLineNum++
      } else if (prefix === '+') {
        // Added line
        result.push({
          type: 'add',
          content: content,
          oldLine: null,
          newLine: newLineNum
        })
        newLineNum++
      }
    }

  }

  return result
}

// Fallback: Simple prefix/suffix diff algorithm
function buildFromStrings(oldString, newString, startLine) {
  const oldLines = oldString ? oldString.split('\n') : []
  const newLines = newString ? newString.split('\n') : []
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

  const baseOldLine = startLine ?? 1
  const baseNewLine = startLine ?? 1

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
}

// Raw diff lines (before context limiting)
const rawDiffLines = computed(() => {
  // Prefer structuredPatch if available
  if (props.structuredPatch && props.structuredPatch.length > 0) {
    return buildFromStructuredPatch(props.structuredPatch)
  }
  // Fallback to string-based diff
  return buildFromStrings(props.oldString, props.newString, props.startLine)
})

// Limit context to 3 lines around changes
const diffLines = computed(() => {
  const lines = rawDiffLines.value
  if (lines.length === 0) return []

  // Find indices of lines that are changes (add/remove)
  const changeIndices = lines
    .map((line, idx) => ({ line, idx }))
    .filter(({ line }) => line.type === 'add' || line.type === 'remove')
    .map(({ idx }) => idx)

  // If no changes, show first few lines only
  if (changeIndices.length === 0) {
    return lines.slice(0, 10)
  }

  // Calculate which line indices to include (change + context)
  const includeIndices = new Set()

  changeIndices.forEach(changeIdx => {
    // Include the change itself
    includeIndices.add(changeIdx)
    // Include context lines before
    for (let i = 1; i <= CONTEXT_LINES; i++) {
      const idx = changeIdx - i
      if (idx >= 0 && lines[idx].type === 'context') {
        includeIndices.add(idx)
      } else {
        break
      }
    }
    // Include context lines after
    for (let i = 1; i <= CONTEXT_LINES; i++) {
      const idx = changeIdx + i
      if (idx < lines.length && lines[idx].type === 'context') {
        includeIndices.add(idx)
      } else {
        break
      }
    }
  })

  // Build result with collapse markers between gaps
  const result = []
  const sortedIndices = Array.from(includeIndices).sort((a, b) => a - b)
  let lastIncludedIdx = -1

  // Process sorted indices, adding collapse markers for gaps
  for (const idx of sortedIndices) {
    const gap = idx - lastIncludedIdx

    // Add collapse marker if there's a gap (more than 1 line skipped)
    if (gap > 1 && lastIncludedIdx >= 0) {
      result.push({
        type: 'collapse',
        linesSkipped: gap - 1
      })
    }

    result.push(lines[idx])
    lastIncludedIdx = idx
  }

  return result
})

const stats = computed(() => {
  const added = rawDiffLines.value.filter(l => l.type === 'add').length
  const removed = rawDiffLines.value.filter(l => l.type === 'remove').length
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
          <template v-for="(line, i) in diffLines" :key="i">
            <!-- Collapse marker row -->
            <tr v-if="line.type === 'collapse'" class="collapse-marker bg-[#1f2937]">
              <td colspan="4" class="text-center py-1.5 text-[#6b7280] select-none">
                <span class="opacity-60">...</span>
                <span class="text-[11px] ml-1.5 opacity-50">({{ line.linesSkipped }} lines)</span>
              </td>
            </tr>

            <!-- Regular diff line row -->
            <tr
              v-else
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
          </template>
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

/* Collapse marker styling */
.collapse-marker td {
  background: #1f2937;
  border-top: 1px dashed #374151;
  border-bottom: 1px dashed #374151;
}

/* Syntax highlighting colors - override for diff context */
.diff-block :deep(.hljs-keyword) { color: #569cd6; }
.diff-block :deep(.hljs-string) { color: #ce9178; }
.diff-block :deep(.hljs-number) { color: #b5cea8; }
.diff-block :deep(.hljs-function) { color: #dcdcaa; }
.diff-block :deep(.hljs-variable) { color: #9cdcfe; }
.diff-block :deep(.hljs-comment) { color: #6a9955; }
</style>
