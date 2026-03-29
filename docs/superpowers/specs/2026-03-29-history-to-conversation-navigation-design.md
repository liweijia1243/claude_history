# History to Conversation Navigation

## Problem

Users browsing command history in the History page cannot easily jump to the full conversation context for a specific command. They must manually navigate Projects → Sessions → find the right conversation, which is tedious and breaks flow.

## Goal

Enable double-click navigation from History entries to the corresponding message position in Conversation, with a one-click return to History preserving search state.

## Approach

Pure frontend routing via `router.push`. History entries already contain `sessionId` and `project` fields from the backend API — no backend changes needed. Use URL query parameters to preserve search state and enable return navigation.

## Design

### Data Flow

1. User double-clicks a History entry
2. Frontend extracts `sessionId` and `project` from the entry
3. Converts `project` path to project ID (replace `/` with `-`, strip leading `-`)
4. Navigates via `router.push('/projects/{projectId}/sessions/{sessionId}?msgTimestamp={ts}&source=history&q={searchQuery}')`

### URL Parameters

| Parameter | Purpose |
|-----------|---------|
| `msgTimestamp` | Timestamp of the history entry, used to locate the specific user message in conversation |
| `source=history` | Indicates the user navigated from History; controls visibility of "Return to History" button |
| `q` | Search query from History page, used to restore search state on return |

### HistoryView Changes

**Click behavior:**
- Single click: expand/collapse the entry to show full command text, complete project path, and precise timestamp
- Double click: navigate to Conversation page at the corresponding message

**Click/double-click conflict resolution:**
- Use a 250ms delay timer on single click
- On double click, cancel the pending single-click timer and execute navigation
- This prevents the expand/collapse flicker on double-click

**Search state URL sync:**
- On search input, update URL via `router.replace({ query: { q: searchQuery } })`
- On page mount, restore search from `route.query.q`
- `router.replace` avoids polluting browser history with every keystroke

**Project ID conversion helper:**
- Frontend utility: `projectPath.replace(/^\//, '').replace(/\//g, '-')`
- Must match the encoding used by the backend for project directory names

### ConversationView Changes

**Message scrolling:**
- On page load, check `route.query.msgTimestamp`
- After conversation rendering completes (use `nextTick`), find the user message matching the timestamp
- Call `scrollIntoView({ behavior: 'smooth' })` to scroll to that message
- No highlight effect — just scroll to position

**"Return to History" button:**
- Visible only when `route.query.source === 'history'`
- Displayed next to the existing back button in the page header
- Same visual style as existing back button (outline variant)
- On click: `router.push('/history?q={route.query.q}')`
- This restores the History page with the previous search query

### No Backend Changes

The existing `/api/history` endpoint already returns `sessionId`, `project`, and `timestamp` for each entry. The existing session endpoint loads conversations by project ID and session ID. No new endpoints or modifications required.

## Files to Modify

| File | Changes |
|------|---------|
| `web/src/views/HistoryView.vue` | Add click/double-click handlers, expand/collapse UI, search URL sync, navigation logic |
| `web/src/views/ConversationView.vue` | Add message scrolling on load, "Return to History" button |
| `web/src/router.js` | No changes needed — query params are handled in components |

## Edge Cases

- **History entry with no matching session**: The session file may have been deleted. The existing error handling in ConversationView (shows "Session not found") is sufficient.
- **Multiple messages with same timestamp**: Unlikely but possible. Use the first match.
- **Empty search on return**: If `q` param is empty/missing, navigate to `/history` without search filter.
- **Browser back button**: Works naturally — the URL has all state, so going back restores History with search.
