<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useEChartsTheme } from '../../composables/useEChartsTheme'

use([PieChart, TooltipComponent, CanvasRenderer])

const props = defineProps({
  totalTokens: { type: Object, default: () => ({ input: 0, output: 0 }) },
})

const { colors, baseOption } = useEChartsTheme()

function formatTokens(n) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

const total = computed(() => props.totalTokens.input + props.totalTokens.output)

const chartOption = computed(() => ({
  ...baseOption.value,
  tooltip: {
    ...baseOption.value.tooltip,
    trigger: 'item',
    formatter: (p) => `${p.name}: ${formatTokens(p.value)} (${p.percent}%)`,
  },
  series: [{
    type: 'pie',
    radius: ['50%', '75%'],
    center: ['35%', '50%'],
    avoidLabelOverlap: false,
    label: {
      show: true,
      position: 'center',
      formatter: () => `{total|${formatTokens(total.value)}}\n{label|总 tokens}`,
      rich: {
        total: { fontSize: 18, fontWeight: 'bold', color: colors.textPrimary, lineHeight: 26 },
        label: { fontSize: 11, color: colors.textSecondary, lineHeight: 16 },
      },
    },
    labelLine: { show: false },
    data: [
      { name: 'Input', value: props.totalTokens.input, itemStyle: { color: colors.blue400 } },
      { name: 'Output', value: props.totalTokens.output, itemStyle: { color: colors.red400 } },
    ],
  }],
}))
</script>

<template>
  <div class="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
    <div class="text-[var(--text-primary)] font-semibold mb-3">Token 用量</div>
    <div class="flex items-center">
      <VChart :option="chartOption" style="height: 160px; flex: 1" autoresize />
      <div class="flex flex-col gap-3 pr-2">
        <div>
          <div class="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
            <span class="w-2 h-2 rounded-full bg-blue-400"></span> Input
          </div>
          <div class="text-lg font-semibold text-blue-400 mt-0.5">{{ formatTokens(totalTokens.input) }}</div>
        </div>
        <div>
          <div class="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
            <span class="w-2 h-2 rounded-full bg-red-400"></span> Output
          </div>
          <div class="text-lg font-semibold text-red-400 mt-0.5">{{ formatTokens(totalTokens.output) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>
