<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useEChartsTheme } from '../../composables/useEChartsTheme'

use([PieChart, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps({
  messageTypes: { type: Object, default: () => ({}) },
})

const { colors, baseOption } = useEChartsTheme()

const total = computed(() =>
  Object.values(props.messageTypes).reduce((a, b) => a + b, 0)
)

const chartOption = computed(() => {
  const typeMap = [
    { key: 'user', name: 'User', color: colors.blue400 },
    { key: 'assistant', name: 'Assistant', color: colors.green400 },
    { key: 'tool_use', name: 'Tool Use', color: colors.amber400 },
    { key: 'tool_result', name: 'Tool Result', color: colors.red400 },
  ]

  const data = typeMap.map(t => ({
    name: t.name,
    value: props.messageTypes[t.key] || 0,
    itemStyle: { color: t.color },
  }))

  return {
    ...baseOption.value,
    tooltip: {
      ...baseOption.value.tooltip,
      trigger: 'item',
      formatter: (p) => `${p.name}: ${p.value.toLocaleString()} (${p.percent}%)`,
    },
    series: [{
      type: 'pie',
      radius: ['50%', '75%'],
      center: ['35%', '50%'],
      avoidLabelOverlap: false,
      label: {
        show: true,
        position: 'center',
        formatter: () => `{total|${total.value.toLocaleString()}}\n{label|总消息}`,
        rich: {
          total: { fontSize: 20, fontWeight: 'bold', color: colors.textPrimary, lineHeight: 28 },
          label: { fontSize: 11, color: colors.textSecondary, lineHeight: 16 },
        },
      },
      labelLine: { show: false },
      data,
    }],
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'middle',
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      itemGap: 12,
      textStyle: { color: colors.textSecondary, fontSize: 12 },
      formatter: (name) => {
        const item = data.find(d => d.name === name)
        const pct = total.value > 0 ? Math.round((item?.value || 0) / total.value * 100) : 0
        return `${name}  ${pct}%`
      },
    },
  }
})
</script>

<template>
  <div class="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
    <div class="text-[var(--text-primary)] font-semibold mb-3">消息类型分布</div>
    <VChart :option="chartOption" style="height: 180px; width: 100%" autoresize />
  </div>
</template>
