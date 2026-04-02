import { computed } from 'vue'

// Color palette matching Tailwind dark theme
const colors = {
  blue400: '#60a5fa',
  green400: '#4ade80',
  purple400: '#c084fc',
  amber400: '#fbbf24',
  red400: '#f87171',
  textPrimary: '#f1f5f9',
  textSecondary: '#94a3b8',
  gridLine: '#334155',
  tooltipBg: '#0f172a',
  tooltipBorder: '#334155',
  cardBg: '#1e293b',
}

export function useEChartsTheme() {
  const baseOption = computed(() => ({
    backgroundColor: 'transparent',
    textStyle: {
      color: colors.textSecondary,
      fontFamily: 'inherit',
    },
    tooltip: {
      backgroundColor: colors.tooltipBg,
      borderColor: colors.tooltipBorder,
      textStyle: { color: colors.textPrimary, fontSize: 12 },
    },
    grid: {
      containLabel: true,
      left: 12,
      right: 12,
      top: 12,
      bottom: 12,
    },
  }))

  return { colors, baseOption }
}
