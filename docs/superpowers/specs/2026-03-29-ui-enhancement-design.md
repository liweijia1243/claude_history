# Claude History Viewer UI Enhancement Design

**Date**: 2026-03-29
**Status**: Draft
**Author**: Claude + User

## Overview

This design specifies UI improvements for the Claude History Viewer web application, focusing on three areas:

1. **Code Block Styling** - Claude Code TUI aesthetic with proper syntax highlighting
2. **Diff Display** - Git diff style with real file line numbers using file-history snapshots
3. **Projects Navigation** - Full-screen project detail view with time-sorted sessions and smart back navigation

## 1. Code Block Styling

### 1.1 Visual Design Goals

Reference: Claude Code TUI appearance

| Element | Specification |
|---------|---------------|
| Background | `#0a0a0a` (very dark) |
| Border | `#262626`, 1px solid |
| Border radius | `0.75rem` (12px) |
| Font | `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas` |
| Font size | `0.875rem` (14px) |
| Line height | `1.6` |

### 1.2 CodeBlock Component Enhancements

**Header bar**:
- File icon (SVG)
- Language label (uppercase, `#a0a0a0`)
- Copy button with hover state

**Syntax highlighting**:
- Use `highlight.js` with `github-dark` theme
- Auto-detect language from file extension
- Fallback to auto-detection if language unknown

### 1.3 DiffBlock Component Enhancements

**Layout**: 4-column table
1. Old line number (right-aligned, `w-10`)
2. New line number (right-aligned, `w-10`)
3. +/- sign column (`w-6`, centered)
4. Code content (left-aligned, expands)

**Colors**:
| Type | Background | Text | Line Number |
|------|------------|------|-------------|
| Context | transparent | `#d1d5db` | `#6b7280` |
| Removed | `#f87171/10` | `#fca5a5` | `#f87171/50` |
| Added | `#4ade80/10` | `#86efac` | `#4ade80/50` |

**Header**:
- Edit icon (orange `#f97316`)
- "Edit" label (orange)
- File path (truncated, gray)
- Stats badges: `-N` (red), `+M` (green)

**Syntax highlighting**:
- Detect language from `filePath` prop
- Apply highlight.js to code content
- Handle multi-line syntax context correctly

## 2. Diff Real Line Numbers (Plan C)

### 2.1 Data Sources

**Session JSONL** contains:
- `file-history-snapshot` messages tracking file versions
- Edit tool uses with `old_string`, `new_string`, `file_path`

**File history storage** (`~/.claude/file-history/`):
```
~/.claude/file-history/
├── <message-id>/
│   ├── <file-hash>@v1    # Backup file content
│   ├── <file-hash>@v2
│   └── ...
```

**Snapshot structure**:
```json
{
  "type": "file-history-snapshot",
  "messageId": "uuid",
  "snapshot": {
    "trackedFileBackups": {
      "path/to/file.py": {
        "backupFileName": "abc123@v2",
        "version": 2,
        "backupTime": "2026-03-13T07:49:19.555Z"
      }
    }
  }
}
```

### 2.2 Backend Algorithm

```python
def enrich_edits_with_line_numbers(messages: list[dict]) -> list[dict]:
    """
    Process session messages and add startLine to Edit tool uses.
    """
    # Step 1: Build file state timeline
    file_timeline = {}  # file_path -> [{"message_id", "backup_file", "time", "idx"}]

    for idx, msg in enumerate(messages):
        if msg.get("type") == "file-history-snapshot":
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

    # Step 2: Process Edit tool uses
    for idx, msg in enumerate(messages):
        if msg.get("type") != "assistant":
            continue

        content = msg.get("message", {}).get("content", [])
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            if block.get("name") != "Edit":
                continue

            input_data = block.get("input", {})
            file_path = input_data.get("file_path", "")
            old_string = input_data.get("old_string", "")

            if not file_path or not old_string:
                continue

            # Find file state before this edit
            state = find_state_before(file_timeline, file_path, idx)
            if not state:
                continue

            # Read backup file
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


def find_state_before(timeline: dict, file_path: str, current_idx: int) -> dict | None:
    """Find the most recent file state before the given message index."""
    states = timeline.get(file_path, [])
    before = [s for s in states if s["idx"] < current_idx]
    return max(before, key=lambda s: s["idx"]) if before else None


def find_string_line(content: str, search_string: str) -> int | None:
    """Find the 1-indexed line number where search_string starts."""
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
```

### 2.3 API Response Enhancement

```javascript
// Tool use in assistant message
{
  "id": "call_xxx",
  "type": "tool_use",
  "name": "Edit",
  "input": {
    "file_path": "/path/to/file.py",
    "old_string": "def old():\n    pass",
    "new_string": "def new():\n    return True"
  },
  "startLine": 42  // NEW: 1-indexed line number where old_string starts
}
```

### 2.4 Frontend Handling

**DiffBlock.vue**:
```vue
<script setup>
const props = defineProps({
  oldString: String,
  newString: String,
  filePath: String,
  startLine: { type: Number, default: null }  // NEW
})

const diffLines = computed(() => {
  // Calculate line numbers
  const baseOldLine = props.startLine ?? 1
  const baseNewLine = props.startLine ?? 1
  // ... diff algorithm ...
})
</script>
```

**Fallback behavior**:
- If `startLine` is `null`: use relative line numbers (1, 2, 3...)
- If file not found in history: same fallback

## 3. Projects Navigation

### 3.1 New Route

```javascript
// router/index.js
{
  path: '/projects/:projectId',
  name: 'ProjectDetail',
  component: () => import('../views/ProjectDetailView.vue')
}
```

### 3.2 ProjectDetailView Design

**Layout**:
```
┌─────────────────────────────────────────────────────────┐
│ [← Back]  /path/to/project                    5 sessions │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │ abc123def456...                                   │  │
│  │ Preview of first user message...         12 msgs  │  │
│  │ Modified: 2026-03-29 14:30                        │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │ def789ghi012...                                   │  │
│  │ Another session preview...                8 msgs  │  │
│  │ Modified: 2026-03-28 10:15                        │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Component structure**:
```vue
<template>
  <div class="project-detail">
    <!-- Header -->
    <header class="h-12 border-b flex items-center px-4 gap-4">
      <button @click="goBack">← Back</button>
      <span class="font-mono text-sm">{{ project?.path }}</span>
      <span class="text-xs text-gray-500">{{ sessions.length }} sessions</span>
    </header>

    <!-- Sessions List -->
    <div class="flex-1 overflow-auto p-6">
      <div class="max-w-3xl mx-auto space-y-3">
        <button
          v-for="session in sessions"
          :key="session.id"
          @click="openSession(session.id)"
          class="w-full text-left p-4 rounded-xl border bg-card hover:bg-assistant"
        >
          <div class="font-mono text-xs text-secondary mb-1">
            {{ session.id.substring(0, 16) }}...
          </div>
          <div class="text-sm truncate">{{ session.preview }}</div>
          <div class="flex justify-between mt-2 text-xs text-secondary">
            <span>{{ session.message_count }} messages</span>
            <span>{{ formatTime(session.modified) }}</span>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>
```

### 3.3 Backend API Changes

**New endpoint**:
```python
@app.get("/api/projects/{project_id}")
def get_project_detail(project_id: str):
    """Get project details with sessions sorted by modification time."""
    project_dir = CLAUDE_DIR / "projects" / project_id
    if not project_dir.exists():
        raise HTTPException(404, "Project not found")

    # Get actual path from first session
    actual_path = get_project_path(project_dir)

    # Get sessions sorted by mtime descending
    sessions = []
    for f in project_dir.glob("*.jsonl"):
        session_info = extract_session_info(f)
        sessions.append(session_info)

    sessions.sort(key=lambda x: x["modified"], reverse=True)

    return {
        "id": project_id,
        "path": actual_path,
        "sessions": sessions
    }
```

**Modified endpoint**:
```python
@app.get("/api/projects/{project_id}/sessions")
def get_project_sessions(project_id: str):
    """List sessions for a project, sorted by modification time (newest first)."""
    # ... existing logic ...
    sessions.sort(key=lambda x: x["modified"], reverse=True)  # ADD THIS
    return sessions
```

### 3.4 Navigation Flow

**Current flow**:
```
ProjectsView → (expand inline) → ConversationView → Back → ProjectsView
```

**New flow**:
```
ProjectsView → ProjectDetailView → ConversationView → Back → ProjectDetailView
```

**ConversationView.vue change**:
```javascript
// Before
function goBack() {
  router.push('/projects')
}

// After
function goBack() {
  router.push(`/projects/${props.projectId}`)
}
```

**ProjectsView.vue change**:
```javascript
// Before: inline expansion
function toggleProject(projectId) {
  expandedProjects.value.has(projectId)
    ? expandedProjects.value.delete(projectId)
    : expandedProjects.value.add(projectId)
}

// After: navigate to detail page
function openProject(projectId) {
  router.push(`/projects/${projectId}`)
}
```

## 4. File Changes Summary

| File | Type | Changes |
|------|------|---------|
| `server.py` | Modify | Add line number calculation, add `/api/projects/{id}` endpoint |
| `web/src/router/index.js` | Create | Add `/projects/:projectId` route |
| `web/src/views/ProjectDetailView.vue` | Create | New project detail page |
| `web/src/views/ProjectsView.vue` | Modify | Change card click to navigation |
| `web/src/views/ConversationView.vue` | Modify | Back button navigates to project detail |
| `web/src/components/DiffBlock.vue` | Modify | Add `startLine` prop, syntax highlighting |
| `web/src/components/CodeBlock.vue` | Modify | TUI style refinements |
| `web/src/components/ToolCallBlock.vue` | Modify | Pass `startLine` to DiffBlock |

## 5. Implementation Order

1. **Backend changes first** (server.py)
   - Add line number calculation in `reconstruct_conversation()`
   - Add `/api/projects/{id}` endpoint
   - Sort sessions by mtime

2. **Router setup**
   - Create `web/src/router/index.js`
   - Add new route

3. **ProjectDetailView**
   - Create new component
   - Update ProjectsView to navigate

4. **ConversationView update**
   - Modify back button logic

5. **DiffBlock enhancement**
   - Add `startLine` prop
   - Add syntax highlighting
   - Update ToolCallBlock to pass data

6. **CodeBlock refinement**
   - TUI style adjustments

## 6. Testing Checklist

- [ ] Code blocks display with syntax highlighting
- [ ] Diff blocks show real line numbers when available
- [ ] Diff blocks fallback to relative line numbers when not available
- [ ] Projects page cards navigate to detail page
- [ ] Project detail shows sessions sorted by modification time (newest first)
- [ ] Conversation back button returns to project detail
- [ ] All views work in both light and dark themes
