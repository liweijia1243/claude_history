# Dashboard 统计图表设计规格

## 概述

为 Dashboard 页面添加丰富的统计图表，覆盖使用频率趋势、项目活跃度、对话内容分析、Token 用量和时段分布等维度，全方位展示 Claude Code 的使用情况。

## 技术选型

- **图表库**：ECharts (vue-echarts)
- **安装依赖**：`echarts` + `vue-echarts`
- **主题**：自定义暗色主题，与现有 Tailwind 暗色 UI 风格一致

## 布局结构

采用"数据驱动仪表盘"布局，自上而下分为四个区域：

```
┌─────────┬─────────┬─────────┬─────────┐
│ Commands│Sessions │Projects │ Tokens  │  ← 统计卡片（带迷你趋势线+环比变化）
└─────────┴─────────┴─────────┴─────────┘
┌───────────────────────────────────────┐
│         活跃度趋势图（全宽）            │  ← 柱状图+折线叠加
│         [7天] [30天] [全部]            │
└───────────────────────────────────────┘
┌───────────┬───────────┬───────────────┐
│ 消息类型   │ 项目Top5  │ 时段分布      │  ← 底部第一行
└───────────┴───────────┴───────────────┘
┌───────────┬───────────┬───────────────┐
│ Token用量  │ 会话时长  │ 最近会话      │  ← 底部第二行
└───────────┴───────────┴───────────────┘
```

响应式：移动端统计卡片 2 列，底部图表单列堆叠。

## 组件详细设计

### 1. 统计卡片（4 张）

| 卡片 | 数据 | 颜色 | 迷你趋势线 | 变化指标 |
|------|------|------|-----------|---------|
| 总命令数 | `total_commands` | blue-400 | 近 7 天每日命令数 | 环比上周百分比 |
| 总会话数 | `total_sessions` | green-400 | 近 7 天每日会话数 | 环比上周百分比 |
| 项目数 | `total_projects` | purple-400 | 近 7 天累计项目数 | 本周新增数 |
| Token 用量 | `total_tokens` | amber-400 | 近 7 天每日 Token 数 | 环比上周百分比 |

每张卡片结构：
- 左上：图标 + 标签
- 左下：大号数值 + 变化率（绿色上升/红色下降，Token 涨多用红色提醒）
- 右下：ECharts sparkline 迷你面积图（60×24px），带渐变填充

**注意**：原第 4 张"Plans"卡片替换为"Token 用量"，Plans 数量信息价值较低。

### 2. 活跃度趋势图

- **图表类型**：ECharts 混合图 — 柱状图（命令数）+ 折线（会话数），双 Y 轴
- **时间范围切换**：右上角按钮组，7天 / 30天 / 全部
- **X 轴**：日期（选"全部"且跨度 > 90 天时自动按周聚合）
- **交互**：tooltip 悬停显示具体日期、命令数、会话数
- **高度**：固定 280px，宽度响应式
- **颜色**：柱状图 blue-400 (opacity 0.7)，折线 amber-400

### 3. 消息类型分布

- **图表类型**：ECharts 环形图（doughnut）
- **分类**：User / Assistant / Tool Use / Tool Result
- **颜色**：blue-400 / green-400 / amber-400 / red-400
- **中心文字**：总消息数
- **右侧图例**：各类型名称 + 百分比

### 4. 项目活跃度 Top 5

- **图表类型**：ECharts 水平柱状图
- **数据**：按会话数排序的前 5 个项目
- **显示**：项目名（路径最后一段）+ 会话数 + 渐变进度条
- **颜色**：purple 渐变，透明度递减
- **交互**：点击可跳转到对应项目页面

### 5. 使用时段分布

- **图表类型**：ECharts 柱状图（24 根柱子）
- **数据**：每小时的命令数汇总
- **颜色**：blue-400，透明度根据值比例变化
- **标注**：底部显示"最活跃时段: HH:00 - HH:00"
- **X 轴**：0, 6, 12, 18, 24

### 6. Token 用量

- **图表类型**：ECharts 环形图
- **分类**：Input Tokens / Output Tokens
- **颜色**：blue-400 / red-400
- **中心文字**：总 Token 数（格式化为 K/M）
- **右侧**：分别显示 Input 和 Output 的具体数值

### 7. 会话时长分布

- **图表类型**：ECharts 水平柱状图
- **区间**：< 5min / 5-15min / 15-30min / 30-60min / > 60min
- **颜色**：绿→黄→红渐变，表示时长递增
- **显示**：区间标签 + 会话数 + 进度条

### 8. 最近会话列表

- 保留现有功能，展示最近 4 条会话
- 每条显示：预览文本、项目名、消息数、时间
- 点击跳转到对话页面
- 右上角"查看全部"链接

## 后端 API 设计

### 新增 `GET /api/dashboard-stats`

#### 请求参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `range` | string | `"30d"` | 时间范围：`7d` / `30d` / `all` |

#### 响应结构

```json
{
  "summary": {
    "total_commands": 1234,
    "total_sessions": 89,
    "total_projects": 12,
    "total_tokens": {
      "input": 840000,
      "output": 1260000
    }
  },
  "changes": {
    "commands_pct": 12.5,
    "sessions_pct": 8.0,
    "projects_new": 2,
    "tokens_pct": 23.0
  },
  "daily_series": [
    {
      "date": "2026-03-03",
      "commands": 42,
      "sessions": 5,
      "tokens": 85000
    }
  ],
  "message_types": {
    "user": 2530,
    "assistant": 2108,
    "tool_use": 1770,
    "tool_result": 2024
  },
  "top_projects": [
    {
      "project_id": "encoded-dir-name",
      "project_name": "claude-history",
      "session_count": 34
    }
  ],
  "hourly_distribution": [12, 8, 5, 3, 2, 5, 10, 20, 45, 70, 85, 75, 50, 65, 90, 100, 80, 60, 50, 55, 65, 50, 35, 20],
  "session_durations": {
    "under_5min": 32,
    "5_to_15min": 40,
    "15_to_30min": 12,
    "30_to_60min": 4,
    "over_60min": 1
  }
}
```

#### 缓存策略

- 内存缓存（Python dict），key 为 `range` 值
- TTL：5 分钟
- 首次请求实时计算，后续请求命中缓存
- 无需主动失效，TTL 过期后自然刷新

#### 数据采集逻辑

- **daily_series**：遍历 `history.jsonl`，按日期聚合命令数；遍历项目会话文件，按修改日期聚合会话数
- **message_types**：遍历范围内的会话 JSONL，统计各 `type` 字段
- **total_tokens**：遍历会话 JSONL 中 assistant 消息的 `usage.input_tokens` 和 `usage.output_tokens`
- **hourly_distribution**：从 `history.jsonl` 的 timestamp 提取小时
- **session_durations**：会话首尾消息时间戳之差
- **top_projects**：按会话文件数排序
- **changes**：对比当前 range 和上一个同等时间段（如 30d 对比前 30d）

## 前端实现要点

### 文件结构

```
web/src/
├── views/Dashboard.vue          # 主页面，组合各图表组件
├── components/dashboard/
│   ├── StatCard.vue              # 统计卡片（含 sparkline）
│   ├── TrendChart.vue            # 活跃度趋势图
│   ├── MessageTypeChart.vue      # 消息类型环形图
│   ├── TopProjectsChart.vue      # 项目活跃度
│   ├── HourlyChart.vue           # 时段分布
│   ├── TokenUsageChart.vue       # Token 用量环形图
│   ├── SessionDurationChart.vue  # 会话时长分布
│   └── RecentSessions.vue        # 最近会话列表
└── composables/
    └── useEChartsTheme.js        # ECharts 暗色主题配置
```

### ECharts 主题

统一暗色主题配置：
- 背景透明（由卡片背景控制）
- 文字颜色：`#94a3b8`（secondary）/ `#f1f5f9`（primary）
- 网格线：`#334155`
- tooltip 背景：`#0f172a`，边框：`#334155`

### 数据流

1. `Dashboard.vue` 的 `onMounted` 调用 `/api/dashboard-stats?range=30d`
2. 数据分发到各子组件 via props
3. 时间范围切换时重新请求 API（range 参数变化）
4. 保留原有 `/api/recent-sessions` 调用给最近会话组件

## 不在本次范围内

- 数据导出功能
- 自定义日期范围选择器
- 图表间的联动筛选
- 持久化缓存（如 Redis/SQLite）
