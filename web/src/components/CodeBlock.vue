<script setup>
import { ref, computed, onMounted } from 'vue'
import hljs from 'highlight.js'
import hljsDefineVue from '../utils/hljsVue.js'

// Register Vue language support
hljs.registerLanguage('vue', hljsDefineVue)

const props = defineProps({
  code: {
    type: String,
    required: true
  },
  language: {
    type: String,
    default: ''
  }
})

const copied = ref(false)
const highlightedCode = ref('')

const displayLanguage = computed(() => {
  if (!props.language) return 'code'
  return props.language
})

onMounted(() => {
  // Apply syntax highlighting
  if (props.code) {
    try {
      if (props.language && hljs.getLanguage(props.language)) {
        highlightedCode.value = hljs.highlight(props.code, { language: props.language }).value
      } else {
        highlightedCode.value = hljs.highlightAuto(props.code).value
      }
    } catch (e) {
      highlightedCode.value = escapeHtml(props.code)
    }
  }
})

function escapeHtml(text) {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

async function copyCode() {
  try {
    await navigator.clipboard.writeText(props.code)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}
</script>

<template>
  <div class="my-3 rounded-xl overflow-hidden border border-[var(--border-color)]">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-2 bg-[#2d2d2d] border-b border-[#404040]">
      <span class="text-xs font-medium text-[#a0a0a0] uppercase tracking-wide">
        {{ displayLanguage }}
      </span>
      <button
        @click="copyCode"
        class="flex items-center gap-1.5 text-xs text-[#a0a0a0] hover:text-[#e0e0e0] transition-colors"
        :title="copied ? 'Copied!' : 'Copy code'"
      >
        <svg v-if="!copied" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
        <span>{{ copied ? 'Copied' : 'Copy' }}</span>
      </button>
    </div>
    <!-- Code content with syntax highlighting -->
    <div class="overflow-x-auto bg-[#1e1e1e]">
      <pre class="!m-0 !p-4 text-[#d4d4d4]"><code v-html="highlightedCode || code"></code></pre>
    </div>
  </div>
</template>

<style scoped>
pre {
  font-size: 0.8125rem;
  line-height: 1.6;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

pre code {
  font-family: inherit;
}
</style>
