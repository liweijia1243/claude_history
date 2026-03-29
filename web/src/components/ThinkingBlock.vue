<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  thinking: String,
})

const expanded = ref(false)

const charCount = computed(() => {
  return (props.thinking?.length || 0).toLocaleString()
})
</script>

<template>
  <div class="my-3">
    <button
      @click="expanded = !expanded"
      class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-dashed border-purple-500/40 bg-purple-500/5 hover:bg-purple-500/10 text-purple-400 transition-colors text-sm"
    >
      <svg
        :class="[expanded ? 'rotate-90' : '']"
        xmlns="http://www.w3.org/2000/svg"
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        class="transition-transform"
      >
        <path d="m9 18 6-6-6-6"/>
      </svg>
      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
      <span class="font-medium">Thinking</span>
      <span class="text-purple-400/60">({{ charCount }} chars)</span>
    </button>

    <Transition name="expand">
      <div
        v-if="expanded"
        class="mt-2 rounded-xl border border-dashed border-purple-500/30 bg-gradient-to-br from-purple-500/5 to-blue-500/5 overflow-hidden"
      >
        <div class="relative max-h-80 overflow-auto">
          <pre class="p-4 text-sm text-purple-300/80 whitespace-pre-wrap break-words font-sans leading-relaxed">{{ thinking }}</pre>
          <!-- Gradient fade at bottom -->
          <div class="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-[var(--bg-page)] to-transparent pointer-events-none"></div>
        </div>
      </div>
    </Transition>
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
  max-height: 400px;
}
</style>
