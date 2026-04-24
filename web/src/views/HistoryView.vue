<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import HistorySearch from '../components/HistorySearch.vue'
import { sourceFromRoute } from '../utils/source'

const route = useRoute()
const source = computed(() => sourceFromRoute(route))
</script>

<template>
  <div class="p-6 max-w-5xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-[var(--text-primary)]">History</h1>
    </div>

    <HistorySearch :source="source" :sync-url="true" :show-project="true" :initially-active="true" />
  </div>
</template>
