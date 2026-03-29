# UI 重构设计文档

**日期：** 2026-03-29
**目标：** 将 Claude History Viewer 的全部页面重构为 ChatGPT/Claude 对话风格，实现精美的 Markdown 渲染和亮/暗双主题。

## 技术方案

保留现有 Vue 3 + Tailwind CSS 技术栈，引入 `@tailwindcss/typography` 插件升级 Markdown 排版。不引入新框架或组件库。

## 1. 全局主题系统

### 亮/暗切换机制

- `<html>` 标签上切换 `class="dark"` 控制
- 侧边栏底部新增主题切换按钮（太阳/月亮图标）
- 偏好存入 `localStorage`，刷新后保持

### 色彩体系（使用 Tailwind `dark:` 前缀）

| 元素 | 暗色 | 亮色 |
|------|------|------|
| 页面背景 | `#0a0a0a` | `#ffffff` |
| 侧边栏 | `#111111` | `#f9fafb` |
| 卡片/气泡 | `#1a1a1a` | `#f3f4f6` |
| 助手消息背景 | `#1e1e1e` | `#f0f0f0` |
| 用户气泡 | `#2563eb` | `#3b82f6` |
| 主文字 | `#e5e5e5` | `#1f2937` |
| 次要文字 | `#9ca3af` | `#6b7280` |
| 边框 | `#262626` | `#e5e7eb` |

## 2. 对话页面（核心重构）

### 用户消息

- 右对齐，蓝色圆角气泡
- 内容渲染 Markdown（不再用 `<pre>`）
- 最大宽度 75%

### 助手消息

- 全宽流式布局（无气泡、无背景框）
- 顶部显示模型图标 + 模型名 + token 用量
- 内容区域直接渲染 Markdown，靠排版本身区分层次
- 类似 ChatGPT 的「干净背景上直接展示内容」

### Markdown 渲染升级

使用 `@tailwindcss/typography` 的 `prose` 类配合自定义样式：

- **标题 h1-h4：** 清晰的字号递减和间距
- **代码块：** 顶部工具栏（语言标签 + 复制按钮）、圆角边框
- **行内代码：** 圆角背景高亮
- **表格：** 斑马纹 + 边框
- **引用块：** 左侧彩色竖线
- **有序/无序列表：** 正确缩进嵌套
- **链接：** 带下划线，悬停变色

新增 `CodeBlock.vue` 组件，替代 marked 默认的 `<pre><code>` 输出。通过 marked 的 renderer 自定义 `code` 块输出为带语言标签和复制按钮的结构。

### 工具调用面板（ToolCallBlock 重写）

- 折叠状态：单行摘要（工具图标 + 工具名 + 文件路径/命令）
- 不同工具类型用不同颜色图标标识
- 展开时平滑动画，内容区带缩进
- Bash 输出用终端风格（深色背景 + 等宽字体）
- Edit/Write 的代码内容用代码块渲染

### Thinking 块

- 默认折叠，显示「思考中... (N 字)」
- 展开时淡紫色虚线边框，最大高度 + 底部渐变遮罩
- 点击切换展开/折叠

## 3. 侧边栏

- 更窄更精致（48px 收起 / 220px 展开）
- 导航项用 SVG 图标替代 emoji
- 底部放主题切换按钮
- 当前页高亮用左侧竖线指示器

## 4. Dashboard

- 统计卡片加图标
- 去掉 Quick Links 区（与侧边栏重复）
- 新增「最近会话」列表，显示最近 5 条会话预览，点击跳转到对话页

## 5. History

- 每条记录左侧显示时间轴线（竖线 + 圆点）
- 按时间分组：「今天」「昨天」「更早」
- 项目路径显示为可点击的 tag/badge

## 6. Plans

- 上方 tab 切换列表，点击切换内容（取代左右分栏）
- Markdown 内容区全宽展示

## 7. Projects

- 项目卡片改为网格布局
- 点击项目在页面内展开 session 列表（不跳转）
- Session 列表项显示消息预览 + 时间 + 消息数

## 文件改动范围

| 文件 | 改动类型 |
|------|----------|
| `web/src/style.css` | 重写，添加主题变量和 prose 自定义样式 |
| `web/src/App.vue` | 重写侧边栏，新增主题切换 |
| `web/src/views/ConversationView.vue` | 重写对话布局和消息样式 |
| `web/src/views/Dashboard.vue` | 重设计 |
| `web/src/views/HistoryView.vue` | 重设计，加时间轴 |
| `web/src/views/PlansView.vue` | 重设计，tab 切换 |
| `web/src/views/ProjectsView.vue` | 重设计，网格布局 |
| `web/src/components/ToolCallBlock.vue` | 重写 |
| `web/src/components/ThinkingBlock.vue` | 重写 |
| `web/src/components/CodeBlock.vue` | 新增 |
| `web/src/composables/useTheme.js` | 新增，主题逻辑 |
| `web/package.json` | 添加 @tailwindcss/typography |

## 不做的事

- 不引入新 UI 框架或组件库
- 不改变后端 API
- 不改变数据读取逻辑
- 不做响应式移动端适配（仅桌面端）
