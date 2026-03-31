# Conversation Toggle Persistence Design

## Problem

The conversation page has four toggle switches (Show Thinking, Show Tools, Show Agents, subagent Show Tools) that reset to defaults every time the user navigates away or refreshes the browser.

## Solution

Persist toggle states to `localStorage` directly within `ConversationView.vue`.

## Changes

**File**: `web/src/views/ConversationView.vue`

1. **Initialize from localStorage**: Read persisted values when creating refs, falling back to current defaults
2. **Watch and save**: Add `watch` on each ref to write to localStorage on change

### localStorage keys

| Key | Default | Ref |
|-----|---------|-----|
| `conv_showThinking` | `false` | `showThinking` |
| `conv_showTools` | `false` | `showTools` |
| `conv_showAgents` | `false` | `showAgents` |
| `conv_subagentShowTools` | `true` | `subagentShowTools` |

## Scope

- No new files
- No dependency changes
- ~10 lines of code changed
