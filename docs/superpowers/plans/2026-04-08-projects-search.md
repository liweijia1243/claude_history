# Projects 搜索功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Projects 页面添加全宽搜索框，实时过滤项目列表

**Architecture:** 纯前端实现。在 ProjectsView.vue 中添加 searchQuery ref 和 filteredProjects computed，模板增加搜索框和空状态提示。

**Tech Stack:** Vue 3 Composition API

---

### Task 1: 添加搜索状态和过滤逻辑

**Files:**
- Modify: `web/src/views/ProjectsView.vue:1-30`

- [ ] **Step 1: 添加 computed 导入和搜索状态**

将 `import { ref, onMounted } from 'vue'` 改为：

```javascript
import { ref, computed, onMounted } from 'vue'
```

在 `const loading = ref(true)` 之后添加：

```javascript
const searchQuery = ref('')

const filteredProjects = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  if (!q) return projects.value
  return projects.value.filter(p => p.path.toLowerCase().includes(q))
})
```

- [ ] **Step 2: 修改模板标题区域（第34-37行）**

替换标题部分：

```html
<h1 class="text-2xl font-bold text-[var(--text-primary)] mb-6 flex items-center gap-3">
  Projects
  <span class="text-sm font-normal text-[var(--text-secondary)]">
    {{ searchQuery ? filteredProjects.length + '/' + projects.length : projects.length }}
  </span>
</h1>
```

- [ ] **Step 3: 在标题和 loading 之间添加搜索框**

在 `</h1>` 之后、`<div v-if="loading">` 之前添加：

```html
<div v-if="!loading" class="relative mb-4">
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-secondary)]">
    <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
  </svg>
  <input
    v-model="searchQuery"
    type="text"
    placeholder="搜索项目路径..."
    class="w-full pl-10 pr-9 py-2.5 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] text-[var(--text-primary)] placeholder:text-[var(--text-secondary)] focus:outline-none focus:border-purple-400/50 transition-colors"
  />
  <button
    v-if="searchQuery"
    @click="searchQuery = ''"
    class="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
  >
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
  </button>
</div>
```

- [ ] **Step 4: 将项目网格的遍历从 projects 改为 filteredProjects**

替换第 43 行的 `v-for="project in projects"` 为：

```html
v-for="project in filteredProjects"
```

- [ ] **Step 5: 在项目网格后添加空状态提示**

在 `</div>` (网格结束标签) 之后、模板最外层 `</div>` 之前添加：

```html
<div v-if="!loading && searchQuery && filteredProjects.length === 0" class="text-center py-12 text-[var(--text-secondary)]">
  <p>未找到匹配 "{{ searchQuery }}" 的项目</p>
</div>
```

- [ ] **Step 6: 启动前端开发服务器验证**

Run: `cd web && npm run dev`

打开 http://localhost:5173/projects 验证：
- 搜索框显示在标题下方
- 输入文字实时过滤项目列表
- 标题数量随过滤变化（如 "5/12"）
- 点击清除按钮清空搜索
- 搜索无匹配时显示空状态提示
- 搜索为空时显示全部项目

- [ ] **Step 7: 提交**

```bash
git add web/src/views/ProjectsView.vue
git commit -m "feat: Projects 页面添加搜索过滤功能"
```
