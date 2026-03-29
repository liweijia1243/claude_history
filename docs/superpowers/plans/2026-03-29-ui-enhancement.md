# UI Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve Claude History Viewer with TUI-style code blocks, git diff with real line numbers, and full-screen project navigation.

**Architecture:** Backend enriches Edit tool uses with line numbers from file-history snapshots. Frontend adds new ProjectDetailView route and enhances DiffBlock with syntax highlighting.

**Tech Stack:** FastAPI (Python), Vue 3, highlight.js, Tailwind CSS v4

---

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `server.py` | Modify | Add line number enrichment, project detail API |
| `web/src/router.js` | Modify | Add `/projects/:projectId` route |
| `web/src/views/ProjectDetailView.vue` | Create | Full-screen project detail page |
| `web/src/views/ProjectsView.vue` | Modify | Navigate to detail instead of expand |
| `web/src/views/ConversationView.vue` | Modify | Back button goes to project detail |
| `web/src/components/DiffBlock.vue` | Modify | Add startLine prop, syntax highlighting |
| `web/src/components/ToolCallBlock.vue` | Modify | Pass startLine to DiffBlock |

---

## Task 1: Backend - Add Line Number Enrichment

**Files:**
- Modify: `server.py`

- [ ] **Step 1: Add helper functions for file-history lookup**

Add these functions after the existing `read_jsonl` function (around line 43):

```python
def find_string_line(content: str, search_string: str) -> int | None:
    """Find the 1-indexed line number where search_string starts."""
    if not content or not search_string:
        return None

    lines = content.split("\n")
    search_lines = search_string.split("\n")
    first_line = search_lines[0] if search_lines else ""

    for i, line in enumerate(lines):
        if line == first_line:
            # Verify full match
            match = True
            for j, search_line in enumerate(search_lines):
                if i + j >= len(lines) or lines[i + j] != search_line:
                    match = False
                    break
            if match:
                return i + 1  # 1-indexed
    return None


def build_file_timeline(messages: list[dict]) -> dict:
    """Build timeline of file states from file-history-snapshot messages."""
    file_timeline = {}  # file_path -> [{"message_id", "backup_file", "time", "idx"}]

    for idx, msg in enumerate(messages):
        if msg.get("type") != "file-history-snapshot":
            continue

        snapshot = msg.get("snapshot", {})
        backups = snapshot.get("trackedFileBackups", {})
        message_id = msg.get("messageId")

        for file_path, info in backups.items():
            file_timeline.setdefault(file_path, []).append({
                "message_id": message_id,
                "backup_file": info.get("backupFileName"),
                "time": info.get("backupTime"),
                "idx": idx
            })

    return file_timeline


def find_state_before(timeline: dict, file_path: str, current_idx: int) -> dict | None:
    """Find the most recent file state before the given message index."""
    states = timeline.get(file_path, [])
    before = [s for s in states if s["idx"] < current_idx]
    return max(before, key=lambda s: s["idx"]) if before else None


def enrich_tool_uses_with_line_numbers(messages: list[dict]) -> list[dict]:
    """Add startLine to Edit tool uses based on file-history snapshots."""
    file_timeline = build_file_timeline(messages)

    for idx, msg in enumerate(messages):
        if msg.get("type") != "assistant":
            continue

        content_blocks = msg.get("message", {}).get("content", [])
        for block in content_blocks:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "tool_use":
                continue
            if block.get("name") != "Edit":
                continue

            input_data = block.get("input", {})
            file_path = input_data.get("file_path", "")
            old_string = input_data.get("old_string", "")

            if not file_path or not old_string:
                continue

            state = find_state_before(file_timeline, file_path, idx)
            if not state:
                continue

            backup_path = CLAUDE_DIR / "file-history" / state["message_id"] / state["backup_file"]
            if not backup_path.exists():
                continue

            try:
                content = backup_path.read_text(encoding="utf-8")
                start_line = find_string_line(content, old_string)
                if start_line is not None:
                    block["startLine"] = start_line
            except Exception:
                pass

    return messages
```

- [ ] **Step 2: Update reconstruct_conversation to use enrichment**

Modify the `reconstruct_conversation` function. Find line 45 and update the function signature and call:

```python
def reconstruct_conversation(messages: list[dict]) -> list[dict]:
    """Reconstruct a conversation thread from raw JSONL messages.

    Groups user messages, assistant messages, and tool results together.
    Enriches Edit tool uses with line numbers from file history.
    """
    # First, enrich tool uses with line numbers
    messages = enrich_tool_uses_with_line_numbers(messages)

    uuid_map = {m.get("uuid"): m for m in messages if m.get("uuid")}
    # ... rest of existing function unchanged ...
```

- [ ] **Step 3: Verify backend changes**

Start the server to ensure no syntax errors:

```bash
cd /home/weijiali/phi_ws/vibe_coding/claude_history && python -c "import server; print('OK')"
```

Expected: `OK`

---

## Task 2: Backend - Add Project Detail API Endpoint

**Files:**
- Modify: `server.py`

- [ ] **Step 1: Add get_project_detail endpoint**

Add after the `get_projects` endpoint (around line 346):

```python
@app.get("/api/projects/{project_id}")
def get_project_detail(project_id: str):
    """Get project details with sessions sorted by modification time."""
    project_dir = CLAUDE_DIR / "projects" / project_id
    if not project_dir.exists():
        raise HTTPException(404, "Project not found")

    # Get actual path from first session's cwd
    actual_path = ""
    sessions_files = list(project_dir.glob("*.jsonl"))
    for sf in sessions_files[:1]:
        msgs = read_jsonl(sf, limit=5)
        for m in msgs:
            cwd = m.get("cwd", "")
            if cwd:
                actual_path = cwd
                break

    # Get sessions sorted by mtime descending
    sessions = []
    for f in project_dir.glob("*.jsonl"):
        messages = read_jsonl(f, limit=10)
        first_msg = next((m for m in messages if m.get("type") == "user"), None)

        preview = ""
        if first_msg:
            content = first_msg.get("message", {}).get("content", "")
            if isinstance(content, str):
                preview = content[:150]
            elif isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
                        preview = c.get("text", "")[:150]
                        break

        stat = f.stat()
        sessions.append({
            "id": f.stem,
            "preview": preview,
            "message_count": len(read_jsonl(f)),
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
        })

    sessions.sort(key=lambda x: x["modified"], reverse=True)

    return {
        "id": project_id,
        "path": actual_path or project_id,
        "sessions": sessions,
    }
```

- [ ] **Step 2: Update get_project_sessions to sort by mtime**

Find the `get_project_sessions` function (around line 349) and add sorting before the return statement:

```python
    # Add before "return sessions" at the end of get_project_sessions
    sessions.sort(key=lambda x: x["modified"], reverse=True)
    return sessions
```

- [ ] **Step 3: Verify backend changes**

```bash
cd /home/weijiali/phi_ws/vibe_coding/claude_history && python -c "import server; print('OK')"
```

Expected: `OK`

---

## Task 3: Frontend - Add Project Detail Route

**Files:**
- Modify: `web/src/router.js`

- [ ] **Step 1: Add ProjectDetailView route**

Update `web/src/router.js`:

```javascript
import { createRouter, createWebHistory } from 'vue-router'

import Dashboard from './views/Dashboard.vue'
import HistoryView from './views/HistoryView.vue'
import PlansView from './views/PlansView.vue'
import ProjectsView from './views/ProjectsView.vue'
import ProjectDetailView from './views/ProjectDetailView.vue'
import ConversationView from './views/ConversationView.vue'

const routes = [
  { path: '/', component: Dashboard },
  { path: '/history', component: HistoryView },
  { path: '/plans', component: PlansView },
  { path: '/projects', component: ProjectsView },
  { path: '/projects/:projectId', component: ProjectDetailView, props: true },
  { path: '/projects/:projectId/sessions/:sessionId', component: ConversationView, props: true },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
```

---

## Task 4: Frontend - Create ProjectDetailView Component

**Files:**
- Create: `web/src/views/ProjectDetailView.vue`

- [ ] **Step 1: Create ProjectDetailView.vue**

```vue
<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = defineProps({
  projectId: String
})

const route = useRoute()
const router = useRouter()
const project = ref(null)
const sessions = ref([])
const loading = ref(true)

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

    <!-- Sessions List -->
    <div class="flex-1 overflow-auto">
      <div v-if="loading" class="text-[var(--text-secondary)] text-center py-16">Loading...</div>

      <div v-else-if="sessions.length === 0" class="text-[var(--text-secondary)] text-center py-16">
        No sessions found
      </div>

      <div v-else class="max-w-3xl mx-auto py-6 px-6 space-y-3">
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
</template>
```

---

## Task 5: Frontend - Update ProjectsView Navigation

**Files:**
- Modify: `web/src/views/ProjectsView.vue`

- [ ] **Step 1: Change toggle to navigation**

Find and replace the `toggleProject` function and related code:

```javascript
// Replace existing code with:
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const projects = ref([])
const loading = ref(true)

onMounted(async () => {
  const res = await fetch('/api/projects')
  projects.value = await res.json()
  loading.value = false
})

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

function truncatePath(path) {
  const parts = path.split('/')
  if (parts.length <= 3) return path
  return '.../' + parts.slice(-3).join('/')
}

function openProject(projectId) {
  router.push(`/projects/${projectId}`)
}
```

- [ ] **Step 2: Update template to use navigation**

Replace the entire `<template>` section:

```vue
<template>
  <div class="p-6 max-w-6xl mx-auto">
    <h1 class="text-2xl font-bold text-[var(--text-primary)] mb-6 flex items-center gap-3">
      Projects
      <span class="text-sm font-normal text-[var(--text-secondary)]">{{ projects.length }}</span>
    </h1>

    <div v-if="loading" class="text-[var(--text-secondary)] py-8 text-center">Loading...</div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <button
        v-for="project in projects"
        :key="project.id"
        @click="openProject(project.id)"
        class="text-left p-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] hover:bg-[var(--bg-assistant)] transition-colors"
      >
        <div class="flex items-center gap-2 mb-2">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-purple-400 flex-shrink-0"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>
          <span class="font-medium text-sm text-[var(--text-primary)] truncate" :title="project.path">
            {{ truncatePath(project.path) }}
          </span>
        </div>
        <div class="flex items-center gap-3 text-xs text-[var(--text-secondary)]">
          <span class="flex items-center gap-1">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/></svg>
            {{ project.session_count }} sessions
          </span>
          <span>{{ formatSize(project.size) }}</span>
        </div>
      </button>
    </div>
  </div>
</template>
```

- [ ] **Step 3: Remove unused styles**

Remove the expand animation styles (no longer needed):

```vue
<style scoped>
/* Remove all existing styles - not needed anymore */
</style>
```

---

## Task 6: Frontend - Update ConversationView Back Navigation

**Files:**
- Modify: `web/src/views/ConversationView.vue`

- [ ] **Step 1: Update goBack function**

Find the `goBack` function (around line 100) and change it:

```javascript
function goBack() {
  router.push(`/projects/${props.projectId}`)
}
```

---

## Task 7: Frontend - Enhance DiffBlock with startLine and Syntax Highlighting

**Files:**
- Modify: `web/src/components/DiffBlock.vue`

- [ ] **Step 1: Add startLine prop and syntax highlighting**

Replace the entire file content:

```vue
<script setup>
import { computed, onMounted, ref } from 'vue'
import hljs from 'highlight.js'

const props = defineProps({
  oldString: {
    type: String,
    default: ''
  },
  newString: {
    type: String,
    default: ''
  },
  filePath: {
    type: String,
    default: ''
  },
  startLine: {
    type: Number,
    default: null
  }
})

// Detect language from file path
const language = computed(() => {
  if (!props.filePath) return null
  const ext = props.filePath.split('.').pop()?.toLowerCase()
  const langMap = {
    'js': 'javascript',
    'ts': 'typescript',
    'vue': 'vue',
    'py': 'python',
    'md': 'markdown',
    'json': 'json',
    'css': 'css',
    'html': 'html',
    'sh': 'bash',
    'bash': 'bash',
    'yaml': 'yaml',
    'yml': 'yaml',
    'toml': 'toml',
    'rs': 'rust',
    'go': 'go',
    'java': 'java',
    'cpp': 'cpp',
    'c': 'c',
    'h': 'c',
  }
  return langMap[ext] || ext
})

// Simple diff algorithm - compute unified diff-style output
const diffLines = computed(() => {
  const oldLines = props.oldString ? props.oldString.split('\n') : []
  const newLines = props.newString ? props.newString.split('\n') : []

  // Simple LCS-based diff
  const result = []

  // Find common prefix and suffix
  let prefixLen = 0
  while (prefixLen < oldLines.length && prefixLen < newLines.length && oldLines[prefixLen] === newLines[prefixLen]) {
    prefixLen++
  }

  let suffixLen = 0
  while (
    suffixLen < oldLines.length - prefixLen &&
    suffixLen < newLines.length - prefixLen &&
    oldLines[oldLines.length - 1 - suffixLen] === newLines[newLines.length - 1 - suffixLen]
  ) {
    suffixLen++
  }

  // Calculate base line numbers
  const baseOldLine = props.startLine ?? 1
  const baseNewLine = props.startLine ?? 1

  // Add common prefix (context)
  for (let i = 0; i < prefixLen; i++) {
    result.push({
      type: 'context',
      content: oldLines[i],
      oldLine: baseOldLine + i,
      newLine: baseNewLine + i
    })
  }

  // Add removed lines
  const removedStart = prefixLen
  const removedEnd = oldLines.length - suffixLen
  for (let i = removedStart; i < removedEnd; i++) {
    result.push({
      type: 'remove',
      content: oldLines[i],
      oldLine: baseOldLine + i,
      newLine: null
    })
  }

  // Add added lines
  const addedStart = prefixLen
  const addedEnd = newLines.length - suffixLen
  for (let i = addedStart; i < addedEnd; i++) {
    result.push({
      type: 'add',
      content: newLines[i],
      oldLine: null,
      newLine: baseNewLine + i
    })
  }

  // Add common suffix (context)
  for (let i = 0; i < suffixLen; i++) {
    const oldIdx = oldLines.length - suffixLen + i
    const newIdx = newLines.length - suffixLen + i
    result.push({
      type: 'context',
      content: oldLines[oldIdx],
      oldLine: baseOldLine + oldIdx,
      newLine: baseNewLine + newIdx
    })
  }

  return result
})

const stats = computed(() => {
  const added = diffLines.value.filter(l => l.type === 'add').length
  const removed = diffLines.value.filter(l => l.type === 'remove').length
  return { added, removed }
})

// Syntax highlighting for each line
const highlightedLines = ref({})

onMounted(() => {
  if (language.value && hljs.getLanguage(language.value)) {
    // Highlight the full old and new strings, then split
    try {
      const oldHighlighted = hljs.highlight(props.oldString, { language: language.value }).value
      const newHighlighted = hljs.highlight(props.newString, { language: language.value }).value

      const oldLinesHl = oldHighlighted.split('\n')
      const newLinesHl = newHighlighted.split('\n')

      // Map content to highlighted content
      const oldLinesRaw = props.oldString.split('\n')
      const newLinesRaw = props.newString.split('\n')

      oldLinesRaw.forEach((line, i) => {
        if (oldLinesHl[i]) {
          highlightedLines.value[line] = oldLinesHl[i]
        }
      })
      newLinesRaw.forEach((line, i) => {
        if (newLinesHl[i]) {
          highlightedLines.value[line] = newLinesHl[i]
        }
      })
    } catch (e) {
      // Fallback to no highlighting
    }
  }
})

function getHighlightedContent(line) {
  return highlightedLines.value[line] || escapeHtml(line)
}

function escapeHtml(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}
</script>

<template>
  <div class="diff-block mt-3 mb-3 rounded-xl overflow-hidden border border-[var(--border-color)]">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-2.5 bg-[#1f2937] border-b border-[#374151]">
      <div class="flex items-center gap-3">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
        <span class="text-xs text-[#f97316] font-medium">Edit</span>
        <span v-if="filePath" class="text-xs text-[#9ca3af] font-mono truncate max-w-[300px]">{{ filePath }}</span>
      </div>
      <div class="flex items-center gap-2 text-xs font-medium">
        <span v-if="stats.removed > 0" class="px-1.5 py-0.5 rounded bg-[#f87171]/20 text-[#f87171]">-{{ stats.removed }}</span>
        <span v-if="stats.added > 0" class="px-1.5 py-0.5 rounded bg-[#4ade80]/20 text-[#4ade80]">+{{ stats.added }}</span>
      </div>
    </div>

    <!-- Diff content -->
    <div class="overflow-x-auto">
      <table class="w-full font-mono text-[13px] leading-[1.5]">
        <tbody>
          <tr
            v-for="(line, i) in diffLines"
            :key="i"
            :class="[
              line.type === 'remove' ? 'bg-[#f87171]/10' : '',
              line.type === 'add' ? 'bg-[#4ade80]/10' : ''
            ]"
          >
            <!-- Old line number -->
            <td
              :class="[
                'w-10 px-2 text-right select-none border-r',
                line.type === 'remove' ? 'text-[#f87171]/50 bg-[#f87171]/5' : '',
                line.type === 'add' ? 'text-transparent border-[#374151]' : 'text-[#6b7280] border-[#374151]',
                line.type === 'context' ? 'text-[#6b7280] border-[#374151]' : ''
              ]"
            >
              {{ line.oldLine ?? '' }}
            </td>
            <!-- New line number -->
            <td
              :class="[
                'w-10 px-2 text-right select-none border-r',
                line.type === 'add' ? 'text-[#4ade80]/50 bg-[#4ade80]/5' : '',
                line.type === 'remove' ? 'text-transparent border-[#374151]' : 'text-[#6b7280] border-[#374151]',
                line.type === 'context' ? 'text-[#6b7280] border-[#374151]' : ''
              ]"
            >
              {{ line.newLine ?? '' }}
            </td>
            <!-- +/- sign -->
            <td
              :class="[
                'w-6 text-center select-none',
                line.type === 'remove' ? 'text-[#f87171] bg-[#f87171]/10' : '',
                line.type === 'add' ? 'text-[#4ade80] bg-[#4ade80]/10' : 'text-[#4b5563]'
              ]"
            >
              {{ line.type === 'remove' ? '-' : line.type === 'add' ? '+' : ' ' }}
            </td>
            <!-- Content with syntax highlighting -->
            <td
              :class="[
                'px-3 whitespace-pre',
                line.type === 'remove' ? 'text-[#fca5a5]' : '',
                line.type === 'add' ? 'text-[#86efac]' : 'text-[#d1d5db]'
              ]"
              v-html="getHighlightedContent(line.content)"
            ></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.diff-block {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
}

table {
  border-collapse: collapse;
  background-color: #111827;
}

td {
  vertical-align: top;
  border: none;
}

/* Syntax highlighting colors - override for diff context */
.diff-block :deep(.hljs-keyword) { color: #569cd6; }
.diff-block :deep(.hljs-string) { color: #ce9178; }
.diff-block :deep(.hljs-number) { color: #b5cea8; }
.diff-block :deep(.hljs-function) { color: #dcdcaa; }
.diff-block :deep(.hljs-variable) { color: #9cdcfe; }
.diff-block :deep(.hljs-comment) { color: #6a9955; }
</style>
```

---

## Task 8: Frontend - Update ToolCallBlock to Pass startLine

**Files:**
- Modify: `web/src/components/ToolCallBlock.vue`

- [ ] **Step 1: Pass startLine to DiffBlock**

Find the DiffBlock usage in the template (around line 132) and add the startLine prop:

```vue
<!-- Edit tool - show diff view -->
<DiffBlock
  v-if="tool.name === 'Edit'"
  :old-string="tool.input?.old_string || ''"
  :new-string="tool.input?.new_string || ''"
  :file-path="tool.input?.file_path || ''"
  :start-line="tool.startLine"
/>
```

---

## Task 9: Testing and Verification

- [ ] **Step 1: Start the backend server**

```bash
cd /home/weijiali/phi_ws/vibe_coding/claude_history && python server.py &
```

- [ ] **Step 2: Start the frontend dev server**

```bash
cd /home/weijiali/phi_ws/vibe_coding/claude_history/web && npm run dev &
```

- [ ] **Step 3: Manual verification checklist**

1. Navigate to `/projects` - should show project cards
2. Click a project card - should navigate to `/projects/:projectId`
3. Verify sessions are sorted by modification time (newest first)
4. Click a session - should navigate to conversation view
5. Click Back button - should return to project detail (not projects list)
6. Find a message with Edit tool use - expand it
7. Verify diff shows real line numbers (if available) or relative line numbers
8. Verify syntax highlighting is applied to diff content

---

## Commit Plan

After completing all tasks:

```bash
git add -A
git commit -m "feat: enhance UI with TUI-style code blocks, real line numbers, and project detail view

- Add file-history-based line number calculation for Edit operations
- Create ProjectDetailView with time-sorted sessions
- Update navigation flow: Projects -> ProjectDetail -> Conversation
- Enhance DiffBlock with startLine prop and syntax highlighting
- Sort sessions by modification time (newest first)"
```
