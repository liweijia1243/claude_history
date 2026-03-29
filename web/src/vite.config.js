<script setup>
import { ref, onMounted } from 'vue'
import { marked } from 'marked'
import 'highlight.js/styles/github-dark.css'
import hljs from 'highlight.js'

// Configure marked with highlight.js
marked.setOptions({
  highlight(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value
    }
    return hljs.highlightAuto(code).value
  },
})

const plans = ref([])
const selectedPlan = ref(null)
const planContent = ref('')
const loading = ref(true)

onMounted(async () => {
  const res = await fetch('/api/plans')
  plans.value = await res.json()
  loading.value = false
})

function formatDate(ts) {
  return new Date(ts * 1000).toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  return (bytes / 1024).toFixed(1) + ' KB'
}

async function selectPlan(plan) {
  selectedPlan.value = plan.name
  const res = await fetch(`/api/plans/${plan.name}`)
  const data = await res.json()
  planContent.value = data.content
}

function renderedMarkdown() {
  if (!planContent.value) return ''
  return marked.parse(planContent.value)
}
</script>

<template>
  <div class="p-6 max-w-6xl mx-auto">
    <h1 class="text-2xl font-bold mb-6">Plans</h1>

    <div v-if="loading" class="text-gray-500">Loading...</div>

    <div v-else-if="plans.length === 0" class="text-gray-500">No plans found.</div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <!-- Plan List -->
      <div class="space-y-2">
        <button
          v-for="plan in plans"
          :key="plan.name"
          @click="selectPlan(plan)"
          :class="[
            selectedPlan === plan.name
              ? 'bg-blue-600/20 border-blue-500/50 text-blue-300'
              : 'bg-gray-900 border-gray-800 text-gray-300 hover:border-gray-600'
          ]"
          class="w-full text-left rounded-xl p-4 border transition-colors"
        >
          <div class="font-medium text-sm truncate">{{ plan.name }}</div>
          <div class="flex items-center gap-3 mt-2 text-xs text-gray-500">
            <span>{{ formatSize(plan.size) }}</span>
            <span>{{ formatDate(plan.modified) }}</span>
          </div>
        </button>
      </div>

      <!-- Plan Content -->
      <div class="lg:col-span-2">
        <div v-if="!selectedPlan" class="text-gray-500 text-center py-16">
          Select a plan to view its content
        </div>
        <div
          v-else
          class="bg-gray-900 rounded-xl border border-gray-800 p-6 prose prose-invert prose-sm max-w-none prose-pre:bg-gray-950 prose-pre:border prose-pre:border-gray-800 prose-code:text-blue-300"
          v-html="renderedMarkdown()"
        ></div>
      </div>
    </div>
  </div>
</template>
