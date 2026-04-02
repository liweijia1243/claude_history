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
  hourlyDistribution: { type: Array, default: () => new Array(24).fill(0) },
})

const { colors, baseOption } = useEChartsTheme()

const peakHour = computed(() => {
  const dist = props.hourlyDistribution
  const maxVal = Math.max(...dist)
  const idx = dist.indexOf(maxVal)
  return maxVal > 0 ? `${idx}:00 - ${idx + 1}:00` : '--'
})

const chartOption = computed(() => {
  const dist = props.hourlyDistribution
  const maxVal = Math.max(...dist, 1)
  const hours = Array.from({ length: 24 }, (_, i) => `${i}`)

  return {
    ...baseOption.value,
    tooltip: {
      ...baseOption.value.tooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => `${params[0].name}:00 — ${params[0].value} 命令`,
    },
    grid: { left: 8, right: 8, top: 4, bottom: 24, containLabel: true },
    xAxis: {
      type: 'category',
      data: hours,
      axisLine: { lineStyle: { color: colors.gridLine } },
      axisTick: { show: false },
      axisLabel: {
        color: colors.textSecondary,
        fontSize: 10,
        interval: 5,
      },
    },
    yAxis: {
      type: 'value',
      show: false,
    },
    series: [{
      type: 'bar',
      data: dist.map(v => ({
        value: v,
        itemStyle: {
          color: colors.blue400,
          opacity: Math.max(0.15, v / maxVal),
          borderRadius: [2, 2, 0, 0],
        },
      })),
      barCategoryGap: '20%',
    }],
  }
})
</script>

<template>
  <div class="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
    <div class="text-[var(--text-primary)] font-semibold mb-1">使用时段分布</div>
    <div class="text-[var(--text-secondary)] text-xs mb-3">一天中各小时的命令数</div>
    <VChart :option="chartOption" style="height: 140px; width: 100%" autoresize />
    <div class="text-center text-xs mt-2">
      <span class="text-blue-400">最活跃时段: </span>
      <span class="text-[var(--text-primary)] font-medium">{{ peakHour }}</span>
    </div>
  </div>
</template>
