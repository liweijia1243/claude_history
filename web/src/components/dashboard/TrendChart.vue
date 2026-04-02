<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useEChartsTheme } from '../../composables/useEChartsTheme'

use([BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps({
  dailySeries: { type: Array, default: () => [] },
  range: { type: String, default: '30d' },
})

const emit = defineEmits(['update:range'])

const { colors, baseOption } = useEChartsTheme()

const chartOption = computed(() => {
  const data = props.dailySeries
  const dates = data.map(d => d.date)
  const commands = data.map(d => d.commands)
  const sessions = data.map(d => d.sessions)

  return {
    ...baseOption.value,
    tooltip: {
      ...baseOption.value.tooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    legend: {
      data: ['每日命令数', '每日会话数'],
      textStyle: { color: colors.textSecondary, fontSize: 12 },
      right: 0,
      top: 0,
      icon: 'roundRect',
      itemWidth: 12,
      itemHeight: 8,
    },
    grid: { left: 12, right: 12, top: 40, bottom: 12, containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: colors.gridLine } },
      axisTick: { show: false },
      axisLabel: {
        color: colors.textSecondary,
        fontSize: 11,
        formatter: (val) => {
          const parts = val.split('-')
          return `${parseInt(parts[1])}/${parseInt(parts[2])}`
        },
      },
    },
    yAxis: [
      {
        type: 'value',
        name: '命令数',
        nameTextStyle: { color: colors.textSecondary, fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: colors.gridLine, type: 'dashed' } },
        axisLabel: { color: colors.textSecondary, fontSize: 11 },
      },
      {
        type: 'value',
        name: '会话数',
        nameTextStyle: { color: colors.textSecondary, fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { color: colors.textSecondary, fontSize: 11 },
      },
    ],
    series: [
      {
        name: '每日命令数',
        type: 'bar',
        data: commands,
        yAxisIndex: 0,
        itemStyle: { color: colors.blue400, borderRadius: [3, 3, 0, 0] },
        opacity: 0.7,
      },
      {
        name: '每日会话数',
        type: 'line',
        data: sessions,
        yAxisIndex: 1,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        showSymbol: false,
        lineStyle: { color: colors.amber400, width: 2 },
        itemStyle: { color: colors.amber400 },
      },
    ],
  }
})

const rangeOptions = [
  { label: '7天', value: '7d' },
  { label: '30天', value: '30d' },
  { label: '全部', value: 'all' },
]
</script>

<template>
  <div class="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
    <div class="flex items-center justify-between mb-4">
      <div>
        <div class="text-[var(--text-primary)] font-semibold">活跃度趋势</div>
        <div class="text-[var(--text-secondary)] text-xs mt-0.5">命令数与会话数变化</div>
      </div>
      <div class="flex gap-1">
        <button
          v-for="opt in rangeOptions"
          :key="opt.value"
          @click="emit('update:range', opt.value)"
          class="text-xs px-3 py-1 rounded-md border transition-colors"
          :class="range === opt.value
            ? 'bg-blue-500/15 text-blue-400 border-blue-500/30'
            : 'text-[var(--text-secondary)] border-[var(--border-color)] hover:text-[var(--text-primary)]'"
        >
          {{ opt.label }}
        </button>
      </div>
    </div>
    <VChart
      :option="chartOption"
      style="height: 280px; width: 100%"
      autoresize
    />
  </div>
</template>
