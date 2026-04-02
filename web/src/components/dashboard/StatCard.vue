<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([LineChart, GridComponent, CanvasRenderer])

const props = defineProps({
  label: String,
  value: [Number, String],
  color: { type: String, default: '#60a5fa' },
  icon: String,
  change: { type: [Number, String], default: 0 },
  changeLabel: { type: String, default: 'vs 上周' },
  sparklineData: { type: Array, default: () => [] },
  invertChangeColor: { type: Boolean, default: false },
})

const formattedValue = computed(() => {
  const v = props.value
  if (typeof v === 'string') return v
  if (v == null) return '0'
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(1) + 'M'
  if (v >= 1_000) return (v / 1_000).toFixed(v >= 10_000 ? 0 : 1) + 'K'
  return v.toLocaleString()
})

const changeIsPositive = computed(() => {
  const n = typeof props.change === 'number' ? props.change : parseFloat(props.change)
  return n > 0
})

const changeColor = computed(() => {
  if (props.change === 0 || props.change === '0') return '#94a3b8'
  if (props.invertChangeColor) return changeIsPositive.value ? '#f87171' : '#4ade80'
  return changeIsPositive.value ? '#4ade80' : '#f87171'
})

const changeText = computed(() => {
  if (typeof props.change === 'string') return props.change
  if (props.change === 0) return '— 0'
  const prefix = props.change > 0 ? '↑' : '↓'
  return `${prefix} ${Math.abs(props.change)}%`
})

const sparklineOption = computed(() => {
  if (!props.sparklineData.length) return null
  return {
    grid: { left: 0, right: 0, top: 0, bottom: 0 },
    xAxis: { type: 'category', show: false, boundaryGap: false },
    yAxis: { type: 'value', show: false },
    series: [{
      type: 'line',
      data: props.sparklineData,
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 2, color: props.color },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: props.color + '4D' },
            { offset: 1, color: props.color + '00' },
          ],
        },
      },
    }],
  }
})
</script>

<template>
  <div class="bg-[var(--bg-card)] rounded-xl p-4 lg:p-5 border border-[var(--border-color)] hover:border-opacity-50 transition-colors">
    <div class="flex items-center gap-2 mb-3">
      <div class="w-8 h-8 rounded-lg flex items-center justify-center" :style="{ background: color + '1A' }">
        <span v-html="icon" class="w-4 h-4" :style="{ color }"></span>
      </div>
      <span class="text-[var(--text-secondary)] text-sm">{{ label }}</span>
    </div>
    <div class="flex items-end justify-between">
      <div>
        <div class="text-2xl lg:text-3xl font-bold" :style="{ color }">{{ formattedValue }}</div>
        <div class="text-xs mt-1">
          <span :style="{ color: changeColor }">{{ changeText }}</span>
          <span class="text-[var(--text-secondary)] ml-1">{{ changeLabel }}</span>
        </div>
      </div>
      <VChart
        v-if="sparklineOption"
        :option="sparklineOption"
        :style="{ width: '64px', height: '28px' }"
        autoresize
      />
    </div>
  </div>
</template>
