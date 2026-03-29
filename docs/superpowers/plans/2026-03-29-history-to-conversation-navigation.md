# History to Conversation Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable double-click navigation from History entries to the corresponding message in Conversation, with one-click return preserving search state.

**Architecture:** Pure frontend routing via `router.push`. The backend adds `project_id` to history items so the frontend doesn't need to guess the project path encoding. URL query parameters carry navigation context (message timestamp, source page, search query) between pages.

**Tech Stack:** Vue 3, Vue Router, FastAPI backend

---

## File Structure

| File | Responsibility |
|------|---------------|
| `server.py` | Add `project_id` to history API response |
| `web/src/views/HistoryView.vue` | Click/double-click handlers, expand/collapse UI, search URL sync, navigation |
| `web/src/views/ConversationView.vue` | Message scroll-to on load, "Return to History" button |

---

### Task 1: Add `project_id` to history API response

**Files:**
- Modify: `server.py:345-381` (the `/api/history` endpoint)

The project path encoding (all non-alphanumeric → `-`) is determined by Claude Code's internal convention and could change. Rather than duplicate it on the frontend, the backend will resolve each history item's `project_id` by checking which project directory contains the session file.

- [ ] **Step 1: Add session-to-project mapping helper to `server.py`**

Add this helper function after the existing `reconstruct_conversation` function (around line 250):

```python
def build_session_project_map():
    """Build a mapping from session_id to project_id by scanning project directories."""
    projects_dir = CLAUDE_DIR / "projects"
    mapping = {}
    if not projects_dir.exists():
        return mapping
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        for session_file in project_dir.glob("*.jsonl"):
            mapping[session_file.stem] = project_dir.name
    return mapping
```

- [ ] **Step 2: Use the mapping in the `/api/history` endpoint**

Inside the `get_history` function, after the `items = history[start : start + limit]` line (around line 373), add:

```python
    # Enrich items with project_id
    session_map = build_session_project_map()
    for item in items:
        sid = item.get("sessionId", "")
        item["project_id"] = session_map.get(sid, "")
```

- [ ] **Step 3: Verify the API returns `project_id`**

Run: `python server.py &` then `curl -s http://localhost:8787/api/history?limit=2 | python3 -m json.tool | grep project_id`

Expected: Each item should now have a `"project_id"` field (e.g. `"-home-weijiali-phi-ws-vibe-coding"`).

- [ ] **Step 4: Commit**

```bash
git add server.py
git commit -m "feat: add project_id to history API response for session navigation"
```

---

### Task 2: HistoryView — search state URL sync

**Files:**
- Modify: `web/src/views/HistoryView.vue`

Add imports for `useRoute`, `useRouter`, and `onMounted`/`watch` for URL query sync. The search box will read from and write to `route.query.q`.

- [ ] **Step 1: Add router imports and restore search from URL on mount**

In `<script setup>`, change the import line:

```javascript
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
```

Add after the existing `const searchTimeout = ref(null)` line:

```javascript
const route = useRoute()
const router = useRouter()

// Restore search from URL query on mount
const initialSearch = route.query.q || ''
search.value = initialSearch
```

Change the existing `onMounted(fetchHistory)` to also include URL restoration:

```javascript
onMounted(() => {
  if (initialSearch) {
    fetchHistory()
  } else {
    fetchHistory()
  }
})
```

(Both branches call `fetchHistory()` — this is just a placeholder for the fact that `search.value` was already set above, so `fetchHistory` will use it.)

- [ ] **Step 2: Sync search to URL query in `onSearchInput`**

Replace the `onSearchInput` function:

```javascript
function onSearchInput() {
  clearTimeout(searchTimeout.value)
  searchTimeout.value = setTimeout(() => {
    page.value = 1
    // Sync search to URL without adding history entries
    router.replace({ path: '/history', query: search.value ? { q: search.value } : {} })
    fetchHistory()
  }, 300)
}
```

- [ ] **Step 3: Test URL sync manually**

Run `cd web && npm run dev`, navigate to `http://localhost:5173/history?q=test`. Verify:
- Search box shows "test"
- Results are filtered
- Typing in search updates the URL

- [ ] **Step 4: Commit**

```bash
git add web/src/views/HistoryView.vue
git commit -m "feat: sync history search state to URL query parameter"
```

---

### Task 3: HistoryView — click to expand, double-click to navigate

**Files:**
- Modify: `web/src/views/HistoryView.vue`

Add expand/collapse state, click/double-click handlers with timer-based conflict resolution, and navigation logic.

- [ ] **Step 1: Add reactive state for expanded items and click timer**

After the existing `const searchTimeout = ref(null)` line, add:

```javascript
const expandedItems = ref(new Set())
const clickTimer = ref(null)
```

- [ ] **Step 2: Add click and double-click handler functions**

Add these functions before the `formatTime` function:

```javascript
function handleClick(item) {
  clearTimeout(clickTimer.value)
  clickTimer.value = setTimeout(() => {
    const key = item.timestamp
    if (expandedItems.value.has(key)) {
      expandedItems.value.delete(key)
    } else {
      expandedItems.value.add(key)
    }
    // Trigger reactivity
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

  const query = {
    msgTimestamp: String(item.timestamp),
    source: 'history',
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
```

- [ ] **Step 3: Update the content card template to support click/double-click and expand**

Replace the content card `<div>` (lines 126-142) with:

```html
            <!-- Content card -->
            <div
              class="bg-[var(--bg-card)]/50 rounded-lg px-4 py-3 hover:bg-[var(--bg-card)] transition-colors border border-transparent hover:border-[var(--border-color)] cursor-pointer"
              @click="handleClick(item)"
              @dblclick="handleDblClick(item)"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="flex-1 min-w-0">
                  <p class="text-sm text-[var(--text-primary)] break-words whitespace-pre-wrap leading-relaxed">{{ item.display }}</p>
                  <div class="flex items-center gap-3 mt-2">
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
              <!-- Expanded details -->
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
```

- [ ] **Step 4: Test click and double-click behavior**

Run the dev server and verify:
- Single click: entry expands to show full path, time, session ID
- Single click again: collapses
- Double click: navigates to conversation page with correct URL params

- [ ] **Step 5: Commit**

```bash
git add web/src/views/HistoryView.vue
git commit -m "feat: add click-to-expand and double-click-to-navigate in history"
```

---

### Task 4: ConversationView — message scrolling on load

**Files:**
- Modify: `web/src/views/ConversationView.vue`

Add `nextTick` import, read `msgTimestamp` from route query, and scroll to the matching user message after the conversation loads.

- [ ] **Step 1: Add `nextTick` to imports and scrolling logic**

Change the import line at the top:

```javascript
import { ref, onMounted, computed, nextTick } from 'vue'
```

Add this function after the existing `goBack` function (around line 102):

```javascript
async function scrollToMessage() {
  const msgTimestamp = route.query.msgTimestamp
  if (!msgTimestamp) return

  await nextTick()
  // Small delay to ensure DOM is fully rendered
  setTimeout(() => {
    const targetMs = Number(msgTimestamp)
    // History timestamps are integer milliseconds; session message timestamps
    // are ISO 8601 strings. They differ by a few ms, so use fuzzy matching
    // (within 1 second tolerance).
    const messages = document.querySelectorAll('[data-msg-timestamp]')
    for (const el of messages) {
      const raw = el.dataset.msgTimestamp
      const elMs = new Date(raw).getTime()
      if (Math.abs(elMs - targetMs) < 1000) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        return
      }
    }
  }, 100)
}
```

- [ ] **Step 2: Call `scrollToMessage` after data loads**

Update the `onMounted` block to call `scrollToMessage` after setting `loading.value = false`:

```javascript
onMounted(async () => {
  const res = await fetch(`/api/projects/${props.projectId}/sessions/${props.sessionId}`)
  const data = await res.json()
  conversation.value = data.conversation
  subagents.value = data.subagents || []
  totalRaw.value = data.total_raw_messages
  loading.value = false
  scrollToMessage()
})
```

- [ ] **Step 3: Add `data-msg-timestamp` attribute to user message elements**

In the template, find the user message `<div>` (around line 179) and add the data attribute:

```html
          <!-- User Message -->
          <div v-if="msg.role === 'user'" class="flex justify-end" :data-msg-timestamp="msg.timestamp">
```

- [ ] **Step 4: Verify timestamp matching works correctly**

The history `timestamp` is integer milliseconds (e.g., `1773387340271`) while session message `timestamp` is ISO 8601 (e.g., `"2026-03-13T07:35:40.273Z"`). They represent the same moment but differ by a few ms. The `scrollToMessage` function handles this with fuzzy matching (1 second tolerance).

Verify by running: `curl -s http://localhost:8787/api/projects/<project_id>/sessions/<session_id> | python3 -c "import json,sys; data=json.load(sys.stdin); [print(m.get('role'), m.get('timestamp','NO_TS')) for m in data['conversation'][:5]]"`

Expected: User messages have ISO 8601 timestamps.

- [ ] **Step 5: Test scroll-to-message**

From History, double-click an entry. Verify the conversation page loads and scrolls to the matching user message.

- [ ] **Step 6: Commit**

```bash
git add web/src/views/ConversationView.vue
git commit -m "feat: scroll to specific message when navigating from history"
```

---

### Task 5: ConversationView — "Return to History" button

**Files:**
- Modify: `web/src/views/ConversationView.vue`

Add a conditional "Return to History" button next to the existing back button.

- [ ] **Step 1: Add a computed property for history source detection**

After the existing `loading = ref(true)` line, add:

```javascript
const fromHistory = computed(() => route.query.source === 'history')
```

- [ ] **Step 2: Add the return-to-history handler function**

After the existing `goBack` function, add:

```javascript
function goBackToHistory() {
  const query = route.query.q ? { q: route.query.q } : {}
  router.push({ path: '/history', query })
}
```

- [ ] **Step 3: Add the button to the header template**

In the header bar (the `<div>` with `class="flex-shrink-0 h-12 ..."`), add the button right after the existing back button:

```html
      <button
        v-if="fromHistory"
        @click="goBackToHistory"
        class="flex items-center gap-1.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors text-sm"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
        History
      </button>
```

- [ ] **Step 4: Test the full navigation loop**

1. Go to `/history`, search for something
2. Double-click an entry → navigates to conversation, scrolls to message
3. Click "History" button → returns to `/history?q=<search>`, search is restored
4. Also test browser back button

- [ ] **Step 5: Commit**

```bash
git add web/src/views/ConversationView.vue
git commit -m "feat: add return-to-history button with search state preservation"
```

---

### Task 6: Final integration test

- [ ] **Step 1: Run the full stack and verify the complete flow**

```bash
./start.sh
```

Test scenarios:
1. History page loads, search works, URL updates
2. Direct URL `/history?q=keyword` restores search
3. Single click expands entry, shows full details
4. Single click again collapses
5. Double click navigates to conversation with correct URL params (`msgTimestamp`, `source`, `q`)
6. Conversation scrolls to matching message
7. "History" button appears in conversation header
8. "History" button returns to history with search restored
9. Browser back button works correctly
10. Entry with no matching session still loads (no crash)

- [ ] **Step 2: Final commit**

```bash
git add -A
git commit -m "feat: history-to-conversation navigation with search state preservation"
```
