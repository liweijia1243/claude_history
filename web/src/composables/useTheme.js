import { ref, watch, onMounted } from 'vue'

const isDark = ref(true)
const initialized = ref(false)

function initTheme() {
  if (initialized.value) return

  const stored = localStorage.getItem('theme')
  if (stored === 'light') {
    isDark.value = false
  } else if (stored === 'dark') {
    isDark.value = true
  } else {
    // Default to system preference
    isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
  }
  applyTheme()
  initialized.value = true
}

function applyTheme() {
  if (isDark.value) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

function toggleTheme() {
  isDark.value = !isDark.value
  applyTheme()
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
}

watch(isDark, applyTheme)

export function useTheme() {
  onMounted(() => {
    initTheme()
  })

  return {
    isDark,
    toggleTheme,
    initTheme,
  }
}
