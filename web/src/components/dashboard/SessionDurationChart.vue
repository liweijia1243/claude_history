<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useEChartsTheme } from '../../composables/useEChartsTheme'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps({
  sessionDurations: {
    type: Object,
    default: () => ({ under_5min: 0, '5_to_15min': 0, '15_to_30min': 0, '30_to_60min': 0, over_60min: 0 }),
  },
})

const { colors, baseOption } = useEChartsTheme()

const buckets = [
  { key: 'under_5min', label: '< 5 min', color: '#4ade80' },
  { key: '5_to_15min', label: '5-15 min', color: '#a3e635' },
  { key: '15_to_30min', label: '15-30 min', color: '#fbbf24' },
  { key: '30_to_60min', label: '30-60 min', color: '#fb923c' },
  { key: 'over_60min', label: '> 60 min', color: '#f87171' },
]

const chartOption = computed(() => {
  const labels = buckets.map(b => b.label).reverse()
  const values = buckets.map(b => props.sessionDurations[b.key] || 0).reverse()
  const barColors = buckets.map(b => b.color).reverse()

  return {
    ...baseOption.value,
    tooltip: {
      ...baseOption.value.tooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => `${params[0].name}: ${params[0].value} 会话`,
    },
    grid: { left: 12, right: 20, top: 4, bottom: 4, containLabel: true },
    xAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: colors.gridLine, type: 'dashed' } },
      axisLabel: { color: colors.textSecondary, fontSize: 11 },
    },
    yAxis: {
      type: 'category',
      data: labels,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: colors.textSecondary, fontSize: 11 },
    },
    series: [{
      type: 'bar',
      data: values.map((v, i) => ({
        value: v,
        itemStyle: { color: barColors[i], borderRadius: [0, 4, 4, 0] },
      })),
      barMaxWidth: 14,
    }],
  }
})
</script>

<template>
  <div class="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
    <div class="text-[var(--text-primary)] font-semibold mb-1">会话时长分布</div>
    <div class="text-[var(--text-secondary)] text-xs mb-3">各时长区间的会话数量</div>
    <VChart :option="chartOption" style="height: 160px; width: 100%" autoresize />
  </div>
</template>
