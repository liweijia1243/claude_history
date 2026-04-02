# Dashboard 统计图表实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Dashboard 添加 ECharts 统计图表，包含趋势图、消息类型分布、项目活跃度、时段分布、Token 用量和会话时长分布。

**Architecture:** 后端新增 `/api/dashboard-stats` 聚合端点（带内存缓存），前端拆分为 8 个 dashboard 子组件 + 1 个 ECharts 主题 composable。Dashboard.vue 作为组合层，通过 props 分发数据到各图表组件。

**Tech Stack:** Python/FastAPI, Vue 3 + ECharts (vue-echarts), Tailwind CSS

---

## File Structure

```
server.py                                    # Modify: 新增 /api/dashboard-stats 端点
web/package.json                             # Modify: 添加 echarts + vue-echarts 依赖
web/src/composables/useEChartsTheme.js       # Create: ECharts 暗色主题配置
web/src/components/dashboard/StatCard.vue    # Create: 统计卡片（含 sparkline）
web/src/components/dashboard/TrendChart.vue  # Create: 活跃度趋势图
web/src/components/dashboard/MessageTypeChart.vue   # Create: 消息类型环形图
web/src/components/dashboard/TopProjectsChart.vue   # Create: 项目活跃度 Top 5
web/src/components/dashboard/HourlyChart.vue        # Create: 时段分布
web/src/components/dashboard/TokenUsageChart.vue     # Create: Token 用量环形图
web/src/components/dashboard/SessionDurationChart.vue # Create: 会话时长分布
web/src/components/dashboard/RecentSessions.vue      # Create: 最近会话列表
web/src/views/Dashboard.vue                  # Modify: 重写为组合各子组件
```

---

### Task 1: 安装 ECharts 依赖

**Files:**
- Modify: `web/package.json`

- [ ] **Step 1: 安装 echarts 和 vue-echarts**

```bash
cd /home/weijiali/phi_ws/vibe_coding/claude_history/web && npm install echarts vue-echarts
```

Expected: `package.json` 中 dependencies 新增 `echarts` 和 `vue-echarts`。

- [ ] **Step 2: 验证安装**

```bash
cd /home/weijiali/phi_ws/vibe_coding/claude_history/web && node -e "require('echarts'); require('vue-echarts'); console.log('OK')"
```

Expected: 输出 `OK`

- [ ] **Step 3: Commit**

```bash
git add web/package.json web/package-lock.json
git commit -m "feat: 安装 echarts 和 vue-echarts 依赖"
```

---

### Task 2: 后端 — `/api/dashboard-stats` 端点

**Files:**
- Modify: `server.py` (在 `get_stats()` 函数之后，约第 346 行)

- [ ] **Step 1: 在 server.py 顶部添加 time import**

在 `server.py` 第 7 行 `import sys` 之后添加：

```python
import time as _time
from collections import defaultdict
```

- [ ] **Step 2: 在 `# ── API Routes ──` 之前添加缓存工具**

在 `server.py` 的 `# ── API Routes ──` 注释行（第 309 行）之前添加：

```python
# ── Dashboard Stats Cache ────────────────────────────────────────────────────

_dashboard_cache: dict = {}  # key: range_str, value: {"data": ..., "ts": float}
_CACHE_TTL = 300  # 5 minutes


def _get_cached_dashboard_stats(range_str: str):
    """Return cached stats if fresh, else None."""
    entry = _dashboard_cache.get(range_str)
    if entry and (_time.time() - entry["ts"]) < _CACHE_TTL:
        return entry["data"]
    return None


def _set_dashboard_cache(range_str: str, data: dict):
    _dashboard_cache[range_str] = {"data": data, "ts": _time.time()}
```

- [ ] **Step 3: 在 `get_stats()` 之后添加 `/api/dashboard-stats` 端点**

在 `server.py` 的 `get_stats()` 函数结束后（`return` 语句之后，`@app.get("/api/recent-sessions")` 之前）添加：

```python
@app.get("/api/dashboard-stats")
def get_dashboard_stats(range: str = Query("30d", pattern="^(7d|30d|all)$")):
    """Get comprehensive dashboard statistics."""
    cached = _get_cached_dashboard_stats(range)
    if cached:
        return cached

    now_ms = datetime.now().timestamp() * 1000
    if range == "7d":
        range_ms = 7 * 86400000
    elif range == "30d":
        range_ms = 30 * 86400000
    else:
        range_ms = None  # all time

    cutoff_ms = (now_ms - range_ms) if range_ms else 0
    prev_cutoff_ms = (cutoff_ms - range_ms) if range_ms else 0

    # ── Read history ──
    history = read_jsonl(CLAUDE_DIR / "history.jsonl")
    history_in_range = [h for h in history if h.get("timestamp", 0) > cutoff_ms]
    history_in_prev = [h for h in history if prev_cutoff_ms < h.get("timestamp", 0) <= cutoff_ms] if range_ms else []

    # ── Daily series from history (commands) ──
    daily_commands = defaultdict(int)
    hourly_dist = [0] * 24
    for h in history_in_range:
        ts = h.get("timestamp", 0)
        if ts:
            dt = datetime.fromtimestamp(ts / 1000)
            day_str = dt.strftime("%Y-%m-%d")
            daily_commands[day_str] += 1
            hourly_dist[dt.hour] += 1

    # ── Scan projects ──
    projects_dir = CLAUDE_DIR / "projects"
    project_dirs = []
    session_files_all = []
    if projects_dir.exists():
        for d in projects_dir.iterdir():
            if d.is_dir():
                project_dirs.append(d)
                for sf in d.glob("*.jsonl"):
                    session_files_all.append((d, sf))

    # ── Per-project session counts & daily sessions ──
    daily_sessions = defaultdict(int)
    project_session_counts = defaultdict(lambda: {"count": 0, "name": "", "id": ""})
    session_files_in_range = []

    for project_dir, sf in session_files_all:
        mtime = sf.stat().st_mtime
        mtime_ms = mtime * 1000
        if mtime_ms > cutoff_ms:
            day_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
            daily_sessions[day_str] += 1
            session_files_in_range.append((project_dir, sf))

        # Count all sessions per project (not just in range) for top projects
        pid = project_dir.name
        project_session_counts[pid]["count"] += 1
        project_session_counts[pid]["id"] = pid

    # ── Resolve project display names ──
    for project_dir in project_dirs:
        pid = project_dir.name
        if pid in project_session_counts and not project_session_counts[pid]["name"]:
            # Try to get actual path from first session
            for sf in project_dir.glob("*.jsonl"):
                msgs = read_jsonl(sf, limit=3)
                for m in msgs:
                    cwd = m.get("cwd", "")
                    if cwd:
                        project_session_counts[pid]["name"] = cwd.rstrip("/").split("/")[-1]
                        break
                break
            if not project_session_counts[pid]["name"]:
                project_session_counts[pid]["name"] = pid

    # ── Top 5 projects ──
    top_projects = sorted(
        project_session_counts.values(),
        key=lambda x: x["count"],
        reverse=True
    )[:5]
    top_projects_out = [
        {"project_id": p["id"], "project_name": p["name"], "session_count": p["count"]}
        for p in top_projects
    ]

    # ── Message types & token usage (sample up to 100 session files in range) ──
    message_types = defaultdict(int)
    total_input_tokens = 0
    total_output_tokens = 0
    session_durations = {"under_5min": 0, "5_to_15min": 0, "15_to_30min": 0, "30_to_60min": 0, "over_60min": 0}
    daily_tokens = defaultdict(int)

    files_to_scan = session_files_in_range if len(session_files_in_range) <= 100 else session_files_in_range[:100]

    for project_dir, sf in files_to_scan:
        msgs = read_jsonl(sf)
        timestamps = []
        for m in msgs:
            msg_type = m.get("type", "")
            if msg_type in ("user", "assistant"):
                message_types[msg_type] += 1
                ts = m.get("timestamp")
                if ts:
                    if isinstance(ts, str):
                        try:
                            ts = datetime.fromisoformat(ts).timestamp() * 1000
                        except (ValueError, TypeError):
                            ts = None
                    if ts:
                        timestamps.append(ts)

            # Count tool_use and tool_result from content blocks
            if msg_type == "assistant":
                content = m.get("message", {}).get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            bt = block.get("type", "")
                            if bt == "tool_use":
                                message_types["tool_use"] += 1

                usage = m.get("message", {}).get("usage", {})
                inp = usage.get("input_tokens", 0)
                out = usage.get("output_tokens", 0)
                total_input_tokens += inp
                total_output_tokens += out

                # Daily tokens
                msg_ts = m.get("timestamp")
                if msg_ts and (inp or out):
                    if isinstance(msg_ts, (int, float)):
                        dt = datetime.fromtimestamp(msg_ts / 1000 if msg_ts > 1e12 else msg_ts)
                    elif isinstance(msg_ts, str):
                        try:
                            dt = datetime.fromisoformat(msg_ts)
                        except (ValueError, TypeError):
                            dt = None
                    if dt:
                        daily_tokens[dt.strftime("%Y-%m-%d")] += inp + out

            if msg_type == "user":
                content = m.get("message", {}).get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            message_types["tool_result"] += 1

        # Session duration
        if len(timestamps) >= 2:
            duration_min = (max(timestamps) - min(timestamps)) / 60000
            if duration_min < 5:
                session_durations["under_5min"] += 1
            elif duration_min < 15:
                session_durations["5_to_15min"] += 1
            elif duration_min < 30:
                session_durations["15_to_30min"] += 1
            elif duration_min < 60:
                session_durations["30_to_60min"] += 1
            else:
                session_durations["over_60min"] += 1

    # ── Build daily series ──
    all_days = sorted(set(list(daily_commands.keys()) + list(daily_sessions.keys()) + list(daily_tokens.keys())))
    daily_series = [
        {
            "date": d,
            "commands": daily_commands.get(d, 0),
            "sessions": daily_sessions.get(d, 0),
            "tokens": daily_tokens.get(d, 0),
        }
        for d in all_days
    ]

    # ── Summary ──
    total_commands = len(history)
    total_sessions = len(session_files_all)
    total_projects = len(project_dirs)

    # ── Changes vs previous period ──
    prev_commands = len(history_in_prev) if range_ms else 0
    curr_commands = len(history_in_range)
    commands_pct = round(((curr_commands - prev_commands) / prev_commands * 100), 1) if prev_commands > 0 else 0

    # Session changes: count sessions modified in prev range
    prev_session_count = 0
    curr_session_count = 0
    for _, sf in session_files_all:
        mtime_ms = sf.stat().st_mtime * 1000
        if mtime_ms > cutoff_ms:
            curr_session_count += 1
        elif range_ms and mtime_ms > prev_cutoff_ms:
            prev_session_count += 1
    sessions_pct = round(((curr_session_count - prev_session_count) / prev_session_count * 100), 1) if prev_session_count > 0 else 0

    # New projects (simplified: just count dirs created in range)
    projects_new = 0
    for d in project_dirs:
        try:
            if d.stat().st_ctime * 1000 > cutoff_ms:
                projects_new += 1
        except OSError:
            pass

    tokens_pct = 0  # Would need previous period token scan; skip for simplicity

    data = {
        "summary": {
            "total_commands": total_commands,
            "total_sessions": total_sessions,
            "total_projects": total_projects,
            "total_tokens": {
                "input": total_input_tokens,
                "output": total_output_tokens,
            },
        },
        "changes": {
            "commands_pct": commands_pct,
            "sessions_pct": sessions_pct,
            "projects_new": projects_new,
            "tokens_pct": tokens_pct,
        },
        "daily_series": daily_series,
        "message_types": dict(message_types),
        "top_projects": top_projects_out,
        "hourly_distribution": hourly_dist,
        "session_durations": session_durations,
    }

    _set_dashboard_cache(range, data)
    return data
```

- [ ] **Step 4: 手动验证端点**

```bash
cd /home/weijiali/phi_ws/vibe_coding/claude_history && python -c "
from server import app
from fastapi.testclient import TestClient
client = TestClient(app)
resp = client.get('/api/dashboard-stats?range=7d')
print(resp.status_code)
data = resp.json()
print('Keys:', list(data.keys()))
print('Summary:', data['summary'])
print('Daily series count:', len(data['daily_series']))
print('Hourly dist len:', len(data['hourly_distribution']))
print('Message types:', data['message_types'])
print('Top projects:', len(data['top_projects']))
"
```

Expected: 200 状态码，返回包含 `summary`, `changes`, `daily_series`, `message_types`, `top_projects`, `hourly_distribution`, `session_durations` 的完整 JSON。

- [ ] **Step 5: Commit**

```bash
git add server.py
git commit -m "feat: 添加 /api/dashboard-stats 聚合统计端点（带缓存）"
```

---

### Task 3: ECharts 暗色主题 Composable

**Files:**
- Create: `web/src/composables/useEChartsTheme.js`

- [ ] **Step 1: 创建 useEChartsTheme.js**

```javascript
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
```

- [ ] **Step 2: Commit**

```bash
git add web/src/composables/useEChartsTheme.js
git commit -m "feat: 添加 ECharts 暗色主题 composable"
```

---

### Task 4: StatCard 组件

**Files:**
- Create: `web/src/components/dashboard/StatCard.vue`

- [ ] **Step 1: 创建 StatCard.vue**

```vue
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
  <div class="bg-[var(--bg-card)] rounded-xl p-4 lg:p-5 border border-[var(--border-color)] hover:border-opacity-50 transition-colors"
       :style="{ '--hover-border': color }"
       :class="`hover:border-[${color}]/30`">
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
```

- [ ] **Step 2: Commit**

```bash
mkdir -p web/src/components/dashboard
git add web/src/components/dashboard/StatCard.vue
git commit -m "feat: 添加 StatCard 统计卡片组件（含 sparkline）"
```

---

### Task 5: TrendChart 趋势图组件

**Files:**
- Create: `web/src/components/dashboard/TrendChart.vue`

- [ ] **Step 1: 创建 TrendChart.vue**

```vue
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
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/dashboard/TrendChart.vue
git commit -m "feat: 添加 TrendChart 活跃度趋势图组件"
```

---

### Task 6: MessageTypeChart 消息类型环形图

**Files:**
- Create: `web/src/components/dashboard/MessageTypeChart.vue`

- [ ] **Step 1: 创建 MessageTypeChart.vue**

```vue
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
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/dashboard/MessageTypeChart.vue
git commit -m "feat: 添加 MessageTypeChart 消息类型环形图组件"
```

---

### Task 7: TopProjectsChart 项目活跃度 Top 5

**Files:**
- Create: `web/src/components/dashboard/TopProjectsChart.vue`

- [ ] **Step 1: 创建 TopProjectsChart.vue**

```vue
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
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/dashboard/TopProjectsChart.vue
git commit -m "feat: 添加 TopProjectsChart 项目活跃度组件"
```

---

### Task 8: HourlyChart 时段分布

**Files:**
- Create: `web/src/components/dashboard/HourlyChart.vue`

- [ ] **Step 1: 创建 HourlyChart.vue**

```vue
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
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/dashboard/HourlyChart.vue
git commit -m "feat: 添加 HourlyChart 时段分布组件"
```

---

### Task 9: TokenUsageChart Token 用量环形图

**Files:**
- Create: `web/src/components/dashboard/TokenUsageChart.vue`

- [ ] **Step 1: 创建 TokenUsageChart.vue**

```vue
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
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/dashboard/TokenUsageChart.vue
git commit -m "feat: 添加 TokenUsageChart Token 用量环形图组件"
```

---

### Task 10: SessionDurationChart 会话时长分布

**Files:**
- Create: `web/src/components/dashboard/SessionDurationChart.vue`

- [ ] **Step 1: 创建 SessionDurationChart.vue**

```vue
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
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/dashboard/SessionDurationChart.vue
git commit -m "feat: 添加 SessionDurationChart 会话时长分布组件"
```

---

### Task 11: RecentSessions 最近会话列表

**Files:**
- Create: `web/src/components/dashboard/RecentSessions.vue`

- [ ] **Step 1: 创建 RecentSessions.vue**

将 Dashboard.vue 中的最近会话列表部分提取为独立组件：

```vue
<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  sessions: { type: Array, default: () => [] },
})

const router = useRouter()

function formatTime(ts) {
  if (!ts) return ''
  const d = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts)
  const now = new Date()
  const diffMs = now - d
  const diffH = diffMs / 3600000

  if (diffH < 24) {
    return d.toLocaleString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  if (diffH < 48) return '昨天'
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit' })
}

function openSession(session) {
  router.push(`/projects/${session.project_id}/sessions/${session.session_id}`)
}
</script>

<template>
  <div class="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
    <div class="flex items-center justify-between mb-3">
      <div class="text-[var(--text-primary)] font-semibold">最近会话</div>
      <router-link to="/projects" class="text-xs text-blue-400 hover:text-blue-300 transition-colors">
        查看全部 →
      </router-link>
    </div>
    <div v-if="sessions.length === 0" class="text-center text-[var(--text-secondary)] text-sm py-6">
      暂无会话
    </div>
    <div v-else class="flex flex-col gap-2">
      <button
        v-for="session in sessions"
        :key="session.session_id"
        @click="openSession(session)"
        class="w-full text-left bg-[var(--bg-page)] rounded-lg p-2.5 hover:bg-[var(--bg-assistant)] transition-colors group"
      >
        <div class="text-xs text-[var(--text-primary)] truncate group-hover:text-blue-400 transition-colors">
          {{ session.preview || 'No preview' }}
        </div>
        <div class="flex items-center gap-2 mt-1.5">
          <span class="text-[10px] text-[var(--text-secondary)] bg-[var(--bg-card)] px-1.5 py-0.5 rounded truncate max-w-[120px]">
            {{ session.project_path }}
          </span>
          <span class="text-[10px] text-[var(--text-secondary)]">{{ session.message_count }} msgs</span>
          <span class="text-[10px] text-[var(--text-secondary)] ml-auto">{{ formatTime(session.timestamp) }}</span>
        </div>
      </button>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/dashboard/RecentSessions.vue
git commit -m "feat: 添加 RecentSessions 最近会话列表组件"
```

---

### Task 12: 重写 Dashboard.vue 组合所有组件

**Files:**
- Modify: `web/src/views/Dashboard.vue`

- [ ] **Step 1: 重写 Dashboard.vue**

完全替换 `web/src/views/Dashboard.vue` 的内容：

```vue
<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import StatCard from '../components/dashboard/StatCard.vue'
import TrendChart from '../components/dashboard/TrendChart.vue'
import MessageTypeChart from '../components/dashboard/MessageTypeChart.vue'
import TopProjectsChart from '../components/dashboard/TopProjectsChart.vue'
import HourlyChart from '../components/dashboard/HourlyChart.vue'
import TokenUsageChart from '../components/dashboard/TokenUsageChart.vue'
import SessionDurationChart from '../components/dashboard/SessionDurationChart.vue'
import RecentSessions from '../components/dashboard/RecentSessions.vue'

const router = useRouter()
const dashboardStats = ref(null)
const recentSessions = ref([])
const loading = ref(true)
const range = ref('30d')

async function fetchDashboardStats() {
  const res = await fetch(`/api/dashboard-stats?range=${range.value}`)
  dashboardStats.value = await res.json()
}

async function fetchRecentSessions() {
  const res = await fetch('/api/recent-sessions?limit=4')
  recentSessions.value = await res.json()
}

onMounted(async () => {
  await Promise.all([fetchDashboardStats(), fetchRecentSessions()])
  loading.value = false
})

watch(range, () => {
  fetchDashboardStats()
})

// ── Sparkline data: last 7 entries from daily_series ──
const last7Days = computed(() => {
  const series = dashboardStats.value?.daily_series || []
  return series.slice(-7)
})

const commandsSparkline = computed(() => last7Days.value.map(d => d.commands))
const sessionsSparkline = computed(() => last7Days.value.map(d => d.sessions))
const tokensSparkline = computed(() => last7Days.value.map(d => d.tokens))

// Projects sparkline: just a flat count (no daily breakdown available)
const projectsSparkline = computed(() => [])

const totalTokens = computed(() => {
  const t = dashboardStats.value?.summary?.total_tokens
  return t ? t.input + t.output : 0
})

// ── Icons (inline SVG strings) ──
const icons = {
  commands: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12 7-7 7 7"/><path d="M12 19V5"/></svg>',
  sessions: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 8h8M8 12h6"/></svg>',
  projects: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>',
  tokens: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
}

function navigateToProject(projectId) {
  router.push(`/projects/${projectId}`)
}
</script>

<template>
  <div class="p-4 lg:p-6 max-w-7xl mx-auto">
    <h1 class="text-2xl font-bold text-[var(--text-primary)] mb-6">Dashboard</h1>

    <div v-if="loading" class="text-[var(--text-secondary)]">Loading...</div>

    <div v-else-if="dashboardStats" class="space-y-4 lg:space-y-6">
      <!-- Stats Cards -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4">
        <StatCard
          label="总命令数"
          :value="dashboardStats.summary.total_commands"
          color="#60a5fa"
          :icon="icons.commands"
          :change="dashboardStats.changes.commands_pct"
          change-label="vs 上周期"
          :sparkline-data="commandsSparkline"
        />
        <StatCard
          label="总会话数"
          :value="dashboardStats.summary.total_sessions"
          color="#4ade80"
          :icon="icons.sessions"
          :change="dashboardStats.changes.sessions_pct"
          change-label="vs 上周期"
          :sparkline-data="sessionsSparkline"
        />
        <StatCard
          label="项目数"
          :value="dashboardStats.summary.total_projects"
          color="#c084fc"
          :icon="icons.projects"
          :change="`+${dashboardStats.changes.projects_new}`"
          change-label="本周期新增"
          :sparkline-data="projectsSparkline"
        />
        <StatCard
          label="Token 用量"
          :value="totalTokens"
          color="#fbbf24"
          :icon="icons.tokens"
          :change="dashboardStats.changes.tokens_pct"
          change-label="vs 上周期"
          :sparkline-data="tokensSparkline"
          :invert-change-color="true"
        />
      </div>

      <!-- Trend Chart -->
      <TrendChart
        :daily-series="dashboardStats.daily_series"
        :range="range"
        @update:range="range = $event"
      />

      <!-- Bottom Row 1: Message Type / Top Projects / Hourly -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-3 lg:gap-4">
        <MessageTypeChart :message-types="dashboardStats.message_types" />
        <TopProjectsChart
          :top-projects="dashboardStats.top_projects"
          @navigate="navigateToProject"
        />
        <HourlyChart :hourly-distribution="dashboardStats.hourly_distribution" />
      </div>

      <!-- Bottom Row 2: Token Usage / Session Duration / Recent Sessions -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-3 lg:gap-4">
        <TokenUsageChart :total-tokens="dashboardStats.summary.total_tokens" />
        <SessionDurationChart :session-durations="dashboardStats.session_durations" />
        <RecentSessions :sessions="recentSessions" />
      </div>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add web/src/views/Dashboard.vue
git commit -m "feat: 重写 Dashboard 页面，组合所有图表组件"
```

---

### Task 13: 端到端验证

**Files:** None (验证步骤)

- [ ] **Step 1: 启动后端**

```bash
cd /home/weijiali/phi_ws/vibe_coding/claude_history && python server.py --no-open &
```

Expected: 服务启动在 8787 端口。

- [ ] **Step 2: 验证 API 返回数据**

```bash
curl -s http://localhost:8787/api/dashboard-stats?range=30d | python -m json.tool | head -30
```

Expected: 格式正确的 JSON，包含 summary、daily_series 等所有字段。

- [ ] **Step 3: 启动前端开发服务器**

```bash
cd /home/weijiali/phi_ws/vibe_coding/claude_history/web && npm run dev
```

Expected: Vite 启动在 5173 端口，无编译错误。

- [ ] **Step 4: 浏览器验证**

打开 `http://localhost:5173`，验证：
1. 4 张统计卡片正常显示数值、sparkline 和变化率
2. 趋势图显示柱状图 + 折线，时间范围切换正常
3. 消息类型环形图正确渲染
4. 项目活跃度 Top 5 显示正确
5. 时段分布 24 根柱子显示正确
6. Token 用量环形图显示 Input/Output
7. 会话时长分布 5 个区间显示正确
8. 最近会话列表可点击跳转
9. 所有图表 tooltip 悬停正常

- [ ] **Step 5: 停止后端进程**

```bash
kill %1  # 停止后台 server.py
```

- [ ] **Step 6: 最终提交（如有调试修改）**

```bash
git add -A
git commit -m "fix: Dashboard 图表调试修复"
```

仅在调试中有修改时执行此步骤。
