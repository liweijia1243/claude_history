# Project History Search 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从 HistoryView.vue 提取 HistorySearch.vue 公共组件，在 ProjectDetailView.vue 中集成 project 内命令搜索功能。

**Architecture:** 提取搜索栏+结果列表为独立组件 `HistorySearch.vue`，通过 props 控制是否过滤 project、是否同步 URL、是否显示项目标签。HistoryView 和 ProjectDetailView 共用此组件。后端零改动。

**Tech Stack:** Vue 3 Composition API, Vue Router, Tailwind CSS

---

## 关键数据映射说明

后端 `/api/history` 的 `project` 参数对 history.jsonl 中的 `project` 字段做子字符串匹配。history.jsonl 的 `project` 字段是实际文件系统路径（如 `/home/user/myproject`），而非目录名（如 `-home-user-myproject`）。因此 HistorySearch 组件接收 `projectPath` prop（实际路径）传给 API，而非 `projectId`（目录名）。

---

### Task 1: 创建 HistorySearch.vue 组件

**Files:**
- Create: `web/src/components/HistorySearch.vue`

- [ ] **Step 1: 创建组件文件**

从 HistoryView.vue 提取搜索逻辑和结果展示。组件接受以下 props：

| Prop | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `projectPath` | `String` | `''` | 传给 API `project` 参数的实际路径 |
| `syncUrl` | `Boolean` | `true` | 是否将搜索词同步到 URL query |
| `showProject` | `Boolean` | `true` | 搜索结果中是否显示项目标签 |
| `fetchOnMount` | `Boolean` | `true` | 是否在挂载时立即加载数据（History 页需要，ProjectDetail 不需要） |

```vue
<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = defineProps({
  projectPath: { type: String, default: '' },
  syncUrl: { type: Boolean, default: true },
  showProject: { type: Boolean, default: true },
  fetchOnMount: { type: Boolean, default: true },
})

const emit = defineEmits(['search-active'])

const items = ref([])
const total = ref(0)
const page = ref(1)
const pages = ref(0)
const search = ref('')
const loading = ref(true)
const searchTimeout = ref(null)

const route = useRoute()
const router = useRouter()

// Restore search from URL query on mount (only when syncUrl is true)
if (props.syncUrl) {
  const initialSearch = route.query.q || ''
  search.value = initialSearch
}

const expandedItems = ref(new Set())
const clickTimer = ref(null)

async function fetchHistory() {
  loading.value = true
  const params = new URLSearchParams({
    page: page.value,
    limit: 50,
    ...(search.value ? { search: search.value } : {}),
    ...(props.projectPath ? { project: props.projectPath } : {}),
  })
  const res = await fetch(`/api/history?${params}`)
  const data = await res.json()
  items.value = data.items
  total.value = data.total
  pages.value = data.pages
  loading.value = false
}

function onSearchInput() {
  clearTimeout(searchTimeout.value)
  searchTimeout.value = setTimeout(() => {
    page.value = 1
    if (props.syncUrl) {
      router.replace({ path: '/history', query: search.value ? { q: search.value } : {} })
    }
    emit('search-active', !!search.value)
    fetchHistory()
  }, 300)
}

function handleClick(item) {
  clearTimeout(clickTimer.value)
  clickTimer.value = setTimeout(() => {
    const key = item.timestamp
    if (expandedItems.value.has(key)) {
      expandedItems.value.delete(key)
    } else {
      expandedItems.value.add(key)
    }
    expandedItems.value = new Set(expandedItems.value)
  }, 250)
}

function handleDblClick(item) {
  clearTimeout(clickTimer.value)
  navigateToConversation(item)
}

function navigateToConversation(item) {
  const projectId = item.project_id
  const sessionId = item.sessionId
  if (!projectId || !sessionId) return

  const source = props.projectPath ? 'project' : 'history'
  const query = {
    msgTimestamp: String(item.timestamp),
    source,
  }
  if (search.value) {
    query.q = search.value
  }
  router.push({
    path: `/projects/${projectId}/sessions/${sessionId}`,
    query,
  })
}

function formatFullTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatDate(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)

  if (d.toDateString() === today.toDateString()) {
    return 'Today'
  } else if (d.toDateString() === yesterday.toDateString()) {
    return 'Yesterday'
  }
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function formatProject(p) {
  if (!p) return ''
  return p.split('/').slice(-2).join('/')
}

const groupedItems = computed(() => {
  const groups = {}
  for (const item of items.value) {
    const dateKey = formatDate(item.timestamp)
    if (!groups[dateKey]) {
      groups[dateKey] = []
    }
    groups[dateKey].push(item)
  }
  return groups
})

onMounted(() => {
  if (props.fetchOnMount) {
    fetchHistory()
  } else {
    loading.value = false
  }
})
watch(page, fetchHistory)
</script>

<template>
  <!-- Search -->
  <div class="mb-6">
    <div class="relative">
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-secondary)]"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
      <input
        v-model="search"
        @input="onSearchInput"
        placeholder="Search commands..."
        class="w-full bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl pl-10 pr-4 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:outline-none focus:border-blue-500/50 transition-colors"
      />
    </div>
  </div>

  <!-- Results area: only show when a search has been performed or fetchOnMount is true -->
  <template v-if="search || fetchOnMount">
    <div v-if="loading" class="text-[var(--text-secondary)] py-8 text-center">Loading...</div>

    <div v-else class="space-y-8">
      <div v-for="(groupItems, dateLabel) in groupedItems" :key="dateLabel">
        <!-- Date header -->
        <div class="flex items-center gap-3 mb-4">
          <h2 class="text-sm font-semibold text-[var(--text-secondary)]">{{ dateLabel }}</h2>
          <div class="flex-1 h-px bg-[var(--border-color)]"></div>
          <span class="text-xs text-[var(--text-secondary)]">{{ groupItems.length }}</span>
        </div>

        <!-- Timeline items -->
        <div class="relative pl-6">
          <div class="absolute left-[7px] top-0 bottom-0 w-px bg-[var(--border-color)]"></div>

          <div
            v-for="item in groupItems"
            :key="item.timestamp"
            class="relative pb-4 last:pb-0"
          >
            <div class="absolute -left-6 top-2 w-3.5 h-3.5 rounded-full border-2 border-[var(--border-color)] bg-[var(--bg-page)]"></div>

            <div
              class="bg-[var(--bg-card)]/50 rounded-lg px-4 py-3 hover:bg-[var(--bg-card)] transition-colors border border-transparent hover:border-[var(--border-color)] cursor-pointer"
              @click="handleClick(item)"
              @dblclick="handleDblClick(item)"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="flex-1 min-w-0">
                  <p class="text-sm text-[var(--text-primary)] break-words whitespace-pre-wrap leading-relaxed">{{ item.display }}</p>
                  <div v-if="showProject" class="flex items-center gap-3 mt-2">
                    <span
                      v-if="item.project"
                      class="inline-flex items-center gap-1 text-xs text-[var(--text-secondary)] bg-[var(--bg-assistant)] px-2 py-0.5 rounded-full"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>
                      {{ formatProject(item.project) }}
                    </span>
                  </div>
                </div>
                <span class="text-xs text-[var(--text-secondary)] flex-shrink-0 whitespace-nowrap">{{ formatTime(item.timestamp) }}</span>
              </div>
              <div v-if="expandedItems.has(item.timestamp)" class="mt-3 pt-3 border-t border-[var(--border-color)] space-y-1.5">
                <div class="text-xs text-[var(--text-secondary)]">
                  <span class="font-medium">Full path:</span> {{ item.project }}
                </div>
                <div class="text-xs text-[var(--text-secondary)]">
                  <span class="font-medium">Time:</span> {{ formatFullTime(item.timestamp) }}
                </div>
                <div class="text-xs text-[var(--text-secondary)]">
                  <span class="font-medium">Session:</span> {{ item.sessionId?.substring(0, 16) }}...
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="pages > 1" class="flex items-center justify-center gap-2 mt-8">
      <button
        @click="page = Math.max(1, page - 1)"
        :disabled="page <= 1"
        class="px-4 py-2 rounded-lg text-sm bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-blue-500/50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        Previous
      </button>
      <span class="text-sm text-[var(--text-secondary)] px-3">{{ page }} / {{ pages }}</span>
      <button
        @click="page = Math.min(pages, page + 1)"
        :disabled="page >= pages"
        class="px-4 py-2 rounded-lg text-sm bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-blue-500/50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        Next
      </button>
    </div>
  </template>
</template>
```

- [ ] **Step 2: 验证组件文件已创建**

Run: `ls -la web/src/components/HistorySearch.vue`
Expected: file exists

- [ ] **Step 3: Commit**

```bash
git add web/src/components/HistorySearch.vue
git commit -m "feat: 提取 HistorySearch 公共搜索组件"
```

---

### Task 2: 重构 HistoryView.vue 使用 HistorySearch 组件

**Files:**
- Modify: `web/src/views/HistoryView.vue`

- [ ] **Step 1: 替换 HistoryView.vue 内容**

将 HistoryView.vue 改为使用 HistorySearch 组件。移除所有已提取到组件中的重复代码（搜索逻辑、结果渲染、格式化函数、跳转逻辑、分页）。

```vue
<script setup>
import HistorySearch from '../components/HistorySearch.vue'
</script>

<template>
  <div class="p-6 max-w-5xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-[var(--text-primary)]">History</h1>
    </div>

    <HistorySearch :sync-url="true" :show-project="true" :fetch-on-mount="true" />
  </div>
</template>
```

注意：原 HistoryView 有 `{{ total }} commands` 计数显示在标题旁。由于 `total` 现在在子组件内部，最简单的做法是暂时移除这个计数（或后续通过事件传递）。遵循 YAGNI，先移除。

- [ ] **Step 2: 验证前端构建通过**

Run: `cd web && npm run build`
Expected: 构建成功，无错误

- [ ] **Step 3: Commit**

```bash
git add web/src/views/HistoryView.vue
git commit -m "refactor: HistoryView 使用 HistorySearch 组件"
```

---

### Task 3: 修改 ProjectDetailView.vue 集成搜索功能

**Files:**
- Modify: `web/src/views/ProjectDetailView.vue`

- [ ] **Step 1: 添加搜索栏和条件显示逻辑**

在 ProjectDetailView 的 header 和 session 列表之间添加搜索栏。搜索有内容时隐藏 session 列表，搜索清空时恢复显示。

完整替换 ProjectDetailView.vue：

```vue
<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import HistorySearch from '../components/HistorySearch.vue'

const props = defineProps({
  projectId: String
})

const route = useRoute()
const router = useRouter()
const project = ref(null)
const sessions = ref([])
const loading = ref(true)
const searchActive = ref(false)

onMounted(async () => {
  const res = await fetch(`/api/projects/${props.projectId}`)
  if (!res.ok) {
    router.push('/projects')
    return
  }
  const data = await res.json()
  project.value = data
  sessions.value = data.sessions
  loading.value = false
})

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function goBack() {
  router.push('/projects')
}

function openSession(sessionId) {
  router.push(`/projects/${props.projectId}/sessions/${sessionId}`)
}

function onSearchActive(active) {
  searchActive.value = active
}
</script>

<template>
  <div class="flex flex-col h-full bg-[var(--bg-page)]">
    <!-- Header -->
    <div class="flex-shrink-0 h-12 border-b border-[var(--border-color)] flex items-center px-4 gap-4 bg-[var(--bg-sidebar)]">
      <button
        @click="goBack"
        class="flex items-center gap-1.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors text-sm"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>
        Back
      </button>
      <div class="flex-1 min-w-0 flex items-center gap-3">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-purple-400 flex-shrink-0"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>
        <span class="font-mono text-sm text-[var(--text-primary)] truncate" :title="project?.path">
          {{ project?.path }}
        </span>
      </div>
      <span class="text-xs text-[var(--text-secondary)]">{{ sessions.length }} sessions</span>
    </div>

    <!-- Content area -->
    <div class="flex-1 overflow-auto">
      <!-- Search bar + results (always rendered, single instance) -->
      <div class="p-6 max-w-5xl mx-auto">
        <HistorySearch
          :project-path="project?.path || ''"
          :sync-url="false"
          :show-project="false"
          :fetch-on-mount="false"
          @search-active="onSearchActive"
        />
      </div>

      <!-- Session list (shown when search is inactive) -->
      <div v-if="!searchActive">
        <div v-if="loading" class="text-[var(--text-secondary)] text-center py-16">Loading...</div>

        <div v-else-if="sessions.length === 0" class="text-[var(--text-secondary)] text-center py-16">
          No sessions found
        </div>

        <div v-else class="max-w-3xl mx-auto pb-6 px-6 space-y-3">
          <button
            v-for="session in sessions"
            :key="session.id"
            @click="openSession(session.id)"
            class="w-full text-left p-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] hover:bg-[var(--bg-assistant)] transition-colors"
          >
            <div class="font-mono text-xs text-[var(--text-secondary)] mb-1">
              {{ session.id.substring(0, 16) }}...
            </div>
            <div v-if="session.preview" class="text-sm text-[var(--text-primary)] truncate">
              {{ session.preview }}
            </div>
            <div v-else class="text-sm text-[var(--text-secondary)] italic">No preview</div>
            <div class="flex justify-between mt-2 text-xs text-[var(--text-secondary)]">
              <span>{{ session.message_count }} messages</span>
              <span>{{ formatTime(session.modified) }}</span>
            </div>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
```

关键设计点：
- 单个 HistorySearch 实例，始终渲染（搜索栏始终可见）
- `fetchOnMount=false`：不在挂载时加载全部历史，只在用户输入搜索词时加载
- 搜索有内容时（`searchActive=true`），HistorySearch 内部显示搜索结果，session 列表被隐藏
- 搜索清空时，HistorySearch 结果区为空，session 列表恢复显示

- [ ] **Step 2: 验证前端构建通过**

Run: `cd web && npm run build`
Expected: 构建成功，无错误

- [ ] **Step 3: Commit**

```bash
git add web/src/views/ProjectDetailView.vue
git commit -m "feat: ProjectDetailView 集成 project 内命令搜索"
```

---

### Task 4: 修改 ConversationView.vue 支持 source=project 返回

**Files:**
- Modify: `web/src/views/ConversationView.vue` (lines 39, 111-156, 170-177)

- [ ] **Step 1: 添加 fromProject computed**

在 line 39 的 `fromHistory` 下方添加 `fromProject`：

```javascript
const fromHistory = computed(() => route.query.source === 'history')
const fromProject = computed(() => route.query.source === 'project')
```

- [ ] **Step 2: 添加 goBackToProject 方法**

在 `goBackToHistory` 方法（line 153-156）后面添加：

```javascript
function goBackToProject() {
  const query = route.query.q ? { q: route.query.q } : {}
  router.push({ path: `/projects/${props.projectId}`, query })
}
```

- [ ] **Step 3: 在 header 中添加 Project 返回按钮**

在现有的 History 按钮（line 170-177）后面，添加 Project 返回按钮：

```html
      <button
        v-if="fromProject"
        @click="goBackToProject"
        class="flex items-center gap-1.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors text-sm"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>
        Project
      </button>
```

此按钮仅在 `source=project` 时显示，点击后返回 project 详情页并保留搜索词。

- [ ] **Step 4: 验证前端构建通过**

Run: `cd web && npm run build`
Expected: 构建成功，无错误

- [ ] **Step 5: Commit**

```bash
git add web/src/views/ConversationView.vue
git commit -m "feat: ConversationView 支持 source=project 返回按钮"
```

---

### Task 5: 端到端验证

- [ ] **Step 1: 启动前后端**

Run: `./start.sh`
Expected: 后端 8787 端口启动，前端 5173 端口启动

- [ ] **Step 2: 手动验证 History 页**

1. 打开 http://localhost:5173/history
2. 验证搜索栏可用，输入搜索词后结果按日期分组显示
3. 单击展开详情，双击跳转到对话页并定位到消息
4. 验证对话页显示 "History" 返回按钮
5. 点击 "History" 返回按钮，验证搜索词保留

- [ ] **Step 3: 手动验证 Project 页**

1. 打开 http://localhost:5173/projects
2. 进入一个 project
3. 验证搜索栏显示在 session 列表上方
4. 输入搜索词，验证 session 列表被搜索结果替换
5. 验证搜索结果中不显示项目标签
6. 清空搜索栏，验证 session 列表恢复显示
7. 双击搜索结果，验证跳转到对话页并定位
8. 验证对话页显示 "Project" 返回按钮
9. 点击 "Project" 返回按钮，验证回到 project 详情页
