<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTheme } from './composables/useTheme'

const router = useRouter()
const route = useRoute()
const { isDark, toggleTheme, initTheme } = useTheme()
const sidebarOpen = ref(true)

onMounted(() => {
  initTheme()
})

const navItems = [
  {
    path: '/',
    label: 'Dashboard',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>`
  },
  {
    path: '/history',
    label: 'History',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg>`
  },
  {
    path: '/plans',
    label: 'Plans',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14,2 14,8 20,8"/><line x1="16" x2="8" y1="13" y2="13"/><line x1="16" x2="8" y1="17" y2="17"/><line x1="10" x2="8" y1="9" y2="9"/></svg>`
  },
  {
    path: '/projects',
    label: 'Projects',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>`
  },
]

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
}

function go(path) {
  router.push(path)
}

function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-[var(--bg-page)]">
    <!-- Sidebar -->
    <aside
      :class="[sidebarOpen ? 'w-[220px]' : 'w-12']"
      class="flex-shrink-0 bg-[var(--bg-sidebar)] border-r border-[var(--border-color)] transition-all duration-200 flex flex-col"
    >
      <!-- Logo -->
      <div class="h-12 flex items-center px-3 border-b border-[var(--border-color)] gap-2">
        <div class="w-6 h-6 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
        </div>
        <span v-if="sidebarOpen" class="font-semibold text-sm text-[var(--text-primary)] truncate">
          Claude History
        </span>
      </div>

      <!-- Nav -->
      <nav class="flex-1 py-2 space-y-0.5 px-1.5">
        <button
          v-for="item in navItems"
          :key="item.path"
          @click="go(item.path)"
          :class="[
            isActive(item.path)
              ? 'text-blue-500 bg-blue-500/10'
              : 'text-[var(--text-secondary)] hover:bg-[var(--bg-card)] hover:text-[var(--text-primary)]'
          ]"
          class="relative w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-colors group"
        >
          <!-- Active indicator -->
          <div
            v-if="isActive(item.path)"
            class="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-blue-500 rounded-r"
          ></div>
          <span class="flex-shrink-0 opacity-80" v-html="item.icon"></span>
          <span v-if="sidebarOpen" class="truncate">{{ item.label }}</span>
        </button>
      </nav>

      <!-- Bottom actions -->
      <div class="border-t border-[var(--border-color)]">
        <!-- Theme toggle -->
        <button
          @click="toggleTheme"
          class="w-full flex items-center gap-2.5 px-3 py-2.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)] transition-colors"
          :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
        >
          <span class="flex-shrink-0">
            <!-- Sun icon -->
            <svg v-if="isDark" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>
            <!-- Moon icon -->
            <svg v-else xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>
          </span>
          <span v-if="sidebarOpen" class="text-sm">{{ isDark ? 'Light Mode' : 'Dark Mode' }}</span>
        </button>

        <!-- Toggle sidebar -->
        <button
          @click="toggleSidebar"
          class="w-full flex items-center justify-center py-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors border-t border-[var(--border-color)]"
        >
          <svg
            :class="[sidebarOpen ? 'rotate-180' : '']"
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="transition-transform"
          >
            <path d="m15 18-6-6 6-6"/>
          </svg>
        </button>
      </div>
    </aside>

    <!-- Main -->
    <main class="flex-1 overflow-auto">
      <router-view />
    </main>
  </div>
</template>
