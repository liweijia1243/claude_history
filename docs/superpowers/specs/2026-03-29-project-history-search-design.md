# Project History Search 设计文档

## 概述

在 ProjectDetailView（会话列表页）中添加搜索栏，允许用户搜索当前 project 下所有会话中发出过的命令。搜索结果以 timeline 样式展示（与 History 页一致），双击可跳转到对应 session 的对话页并自动定位到该消息。

## 需求

- 搜索范围：当前 project 下的用户命令（复用 `/api/history` API，传入 `project` 参数）
- 搜索栏位置：ProjectDetailView header 下方
- 搜索激活时：替换 session 列表，显示搜索结果
- 搜索栏清空时：恢复显示 session 列表
- 双击搜索结果：跳转到 `/projects/{projectId}/sessions/{sessionId}?msgTimestamp=xxx&source=project`，自动定位到该消息
- 搜索结果中不显示项目标签（因为都在同一个 project 内）

## 实现方案

### 1. 新建 `HistorySearch.vue` 组件

从 `HistoryView.vue` 提取搜索和结果展示逻辑为独立组件。

**Props:**

| Prop | 类型 | 说明 |
|------|------|------|
| `projectId` | `string?` | 限定搜索范围的 project ID，传给 API `project` 参数 |
| `syncUrl` | `boolean` | 是否将搜索词同步到 URL query（History 页需要，ProjectDetail 不需要） |
| `showProject` | `boolean` | 搜索结果中是否显示项目标签（默认 true） |

**功能:**

- 搜索栏（300ms debounce）
- Timeline 样式结果列表（按日期分组）
- 单击展开详情、双击跳转到对话并定位
- 分页
- 当 `projectId` 存在时，API 请求附带 `project=projectId` 过滤
- 跳转 query 中 `source` 字段：有 `projectId` 时为 `project`，否则为 `history`

### 2. 改造 `HistoryView.vue`

用 `<HistorySearch :sync-url="true" :show-project="true" />` 替换现有的搜索栏和结果列表部分。移除被提取到组件中的重复代码（搜索逻辑、结果渲染、格式化函数、跳转逻辑）。

### 3. 改造 `ProjectDetailView.vue`

- 在 header 下方添加 `<HistorySearch>` 组件
- 传入 `:project-id="projectId"` `:sync-url="false"` `:show-project="false"`
- 当搜索栏有内容时隐藏 session 列表，显示搜索结果
- 搜索栏为空时显示 session 列表

### 4. `ConversationView.vue` 微调

- `scrollToMessage()` 已支持按 `msgTimestamp` 定位，无需改动
- 返回按钮逻辑：当 `source=project` 时返回到 `/projects/{projectId}` 并恢复搜索状态（通过 URL query `q` 参数）

### 5. 后端

零改动。`/api/history` 已支持 `project` 参数过滤。

## 文件变更清单

| 文件 | 变更类型 |
|------|----------|
| `web/src/components/HistorySearch.vue` | 新建 |
| `web/src/views/HistoryView.vue` | 重构：用组件替换内联代码 |
| `web/src/views/ProjectDetailView.vue` | 修改：添加搜索组件 |
| `web/src/views/ConversationView.vue` | 微调：返回按钮支持 `source=project` |
