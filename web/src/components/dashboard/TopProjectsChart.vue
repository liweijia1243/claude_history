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
  topProjects: { type: Array, default: () => [] },
})

const emit = defineEmits(['navigate'])

const { colors, baseOption } = useEChartsTheme()

const chartOption = computed(() => {
  const projects = [...props.topProjects].reverse()
  const names = projects.map(p => p.project_name)
  const values = projects.map(p => p.session_count)

  return {
    ...baseOption.value,
    tooltip: {
      ...baseOption.value.tooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const p = params[0]
        return `${p.name}: ${p.value} 会话`
      },
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
      data: names,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: colors.textSecondary,
        fontSize: 11,
        width: 80,
        overflow: 'truncate',
      },
    },
    series: [{
      type: 'bar',
      data: values,
      barMaxWidth: 16,
      itemStyle: {
        borderRadius: [0, 4, 4, 0],
        color: {
          type: 'linear', x: 0, y: 0, x2: 1, y2: 0,
          colorStops: [
            { offset: 0, color: colors.purple400 },
            { offset: 1, color: '#a855f7' },
          ],
        },
      },
    }],
  }
})

function handleClick(params) {
  if (params.componentType === 'series') {
    const idx = props.topProjects.length - 1 - params.dataIndex
    const project = props.topProjects[idx]
    if (project) {
      emit('navigate', project.project_id)
    }
  }
}
</script>

<template>
  <div class="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
    <div class="text-[var(--text-primary)] font-semibold mb-3">项目活跃度 Top 5</div>
    <VChart
      :option="chartOption"
      style="height: 180px; width: 100%"
      autoresize
      @click="handleClick"
    />
  </div>
</template>
