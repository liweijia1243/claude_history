# TUI-Style Diff Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the web diff display match the TUI style: correct unified diff format with proper line numbers, limited context (3 lines), and collapsed unchanged sections with "..." markers.

**Architecture:**
1. Keep the existing prefix/suffix diff algorithm for finding changes
2. Add a new `limitedDiffLines` computed property that limits context to 3 lines and inserts collapse markers
3. Fix line number calculation to show final file line numbers correctly
4. Update template to handle collapse markers

**Tech Stack:** Vue 3, JavaScript (no external diff library)

---

## Problem Analysis

### Current Issues

1. **Too much context**: All context lines shown, making diffs verbose
2. **No collapsing**: Large unchanged sections displayed fully
3. **Visual mismatch**: Doesn't match TUI's compact style

### Expected TUI Output
```
Update(web/src/utils/ansiToHtml.js)
  ⎿  Added 6 lines, removed 2 lines
      51        const r = parts[i + 2]
      52        const g = parts[i + 3]
      53        const b = parts[i + 4]
      54 -      if (r !== undefined && g !== undefined && b !== undefined) {
      54 +      if (isValidRgb(r, g, b)) {
      55          style += `color:rgb(${r},${g},${b});`
      ...
      63        const r = parts[i + 2]
```

Key features:
- Only 3 context lines before/after changes
- "..." markers between separated hunks
- Line numbers from final file

---

## File Structure

**Files to Modify:**
- `web/src/components/DiffBlock.vue` - Main diff display component

---

## Task 1: Add Context Constant and Find Change Indices

**Files:**
- Modify: `web/src/components/DiffBlock.vue`

- [ ] **Step 1: Add CONTEXT_LINES constant after the props definition**

Add this constant after line 26 (after the props definition):

```javascript
const CONTEXT_LINES = 3
```

- [ ] **Step 2: Verify the constant is added correctly**

The code should look like:

```javascript
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

const CONTEXT_LINES = 3
```

---

## Task 2: Implement Context Limiting with Collapse Markers

**Files:**
- Modify: `web/src/components/DiffBlock.vue:130`

- [ ] **Step 1: Add limitedDiffLines computed property after diffLines**

Add this new computed property right after the `diffLines` computed property (around line 130, before `stats`):

```javascript
// Limit context lines and add collapse markers
const limitedDiffLines = computed(() => {
  const lines = diffLines.value
  if (lines.length === 0) return []

  // Find indices of lines that are changes (add/remove)
  const changeIndices = lines
    .map((line, idx) => ({ line, idx }))
    .filter(({ line }) => line.type === 'add' || line.type === 'remove')
    .map(({ idx }) => idx)

  // If no changes, show first few lines only
  if (changeIndices.length === 0) {
    return lines.slice(0, 10)
  }

  // Calculate which line indices to include (change + context)
  const includeIndices = new Set()

  changeIndices.forEach(changeIdx => {
    // Include the change itself
    includeIndices.add(changeIdx)
    // Include context lines before
    for (let i = 1; i <= CONTEXT_LINES; i++) {
      if (changeIdx - i >= 0) includeIndices.add(changeIdx - i)
    }
    // Include context lines after
    for (let i = 1; i <= CONTEXT_LINES; i++) {
      if (changeIdx + i < lines.length) includeIndices.add(changeIdx + i)
    }
  })

  // Build result with collapse markers between gaps
  const result = []
  const sortedIndices = Array.from(includeIndices).sort((a, b) => a - b)
  let lastIncludedIdx = -1

  sortedIndices.forEach(idx => {
    const gap = idx - lastIncludedIdx

    // Add collapse marker if there's a gap
    if (gap > 1 && lastIncludedIdx >= 0) {
      result.push({
        type: 'collapse',
        linesSkipped: gap - 1
      })
    }

    result.push(lines[idx])
    lastIncludedIdx = idx
  })

  return result
})
```

- [ ] **Step 2: Verify the computed property is added correctly**

Run the dev server and check for any syntax errors:

```bash
cd web && npm run dev
```

Expected: No console errors related to DiffBlock.vue

---

## Task 3: Update Template to Use limitedDiffLines

**Files:**
- Modify: `web/src/components/DiffBlock.vue:238-288`

- [ ] **Step 1: Replace `diffLines` with `limitedDiffLines` and add collapse handling**

Replace the entire `<tbody>` section (lines 237-288) with:

```vue
        <tbody>
          <template v-for="(line, i) in limitedDiffLines" :key="i">
            <!-- Collapse marker row -->
            <tr v-if="line.type === 'collapse'" class="collapse-marker">
              <td colspan="4" class="text-center py-1 text-[#6b7280] select-none">
                <span class="opacity-60">...</span>
                <span class="text-xs ml-1 opacity-40">({{ line.linesSkipped }} lines)</span>
              </td>
            </tr>

            <!-- Regular diff line row -->
            <tr
              v-else
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
          </template>
        </tbody>
```

- [ ] **Step 2: Verify the template renders correctly**

Open the browser and navigate to a conversation with an Edit tool call.

Expected:
- Context lines limited to 3 before/after changes
- "..." markers appear between separated hunks
- No console errors

---

## Task 4: Add Styles for Collapse Marker

**Files:**
- Modify: `web/src/components/DiffBlock.vue:294-316`

- [ ] **Step 1: Add collapse marker style to the scoped style section**

Add this style rule after line 315 (after the last `.diff-block :deep()` rule):

```css
.collapse-marker td {
  background: repeating-linear-gradient(
    90deg,
    transparent,
    transparent 4px,
    #374151 4px,
    #374151 8px
  );
  background-position: center;
  background-repeat: repeat-x;
  background-size: 8px 1px;
}
```

- [ ] **Step 2: Verify styles are applied**

Check that the collapse marker has a subtle dotted line background.

---

## Task 5: Update Copy Diff Text Generation

**Files:**
- Modify: `web/src/components/DiffBlock.vue:141-148`

- [ ] **Step 1: Update diffText computed to use limitedDiffLines**

Change the `diffText` computed property (around line 141) to use `limitedDiffLines` instead of `diffLines`:

```javascript
const diffText = computed(() => {
  return limitedDiffLines.value.map(line => {
    if (line.type === 'collapse') {
      return `... (${line.linesSkipped} lines skipped)`
    }
    const oldLineStr = line.oldLine?.toString().padStart(4, ' ') ?? '    '
    const newLineStr = line.newLine?.toString().padStart(4, ' ') ?? '    '
    const sign = line.type === 'remove' ? '-' : line.type === 'add' ? '+' : ' '
    return `${oldLineStr} ${newLineStr} ${sign} ${line.content}`
  }).join('\n')
})
```

- [ ] **Step 2: Test copy functionality**

Click the "Copy" button and paste into a text editor.

Expected: Copied text includes "..." markers and matches the displayed diff.

---

## Task 6: Final Verification

- [ ] **Step 1: Start the application**

```bash
./start.sh
```

- [ ] **Step 2: Navigate to a conversation with multiple Edit tool calls**

Open: `http://localhost:8787/projects/-home-weijiali-phi-ws-vibe-coding-claude-history/sessions/f6a3dc9e-a6ef-47d9-8b85-0a8894cf8761`

- [ ] **Step 3: Verify the diff display**

Compare with TUI output:
1. Line numbers should match (starting from `startLine`)
2. Context should be limited to 3 lines
3. "..." should appear between separated hunks
4. Stats should show correct +/- counts

---

## Task 7: Commit Changes

- [ ] **Step 1: Check git status**

```bash
git status
git diff web/src/components/DiffBlock.vue
```

- [ ] **Step 2: Commit the changes**

```bash
git add web/src/components/DiffBlock.vue
git commit -m "$(cat <<'EOF'
fix: 改进 diff 显示，匹配 TUI 风格

- 添加 context 限制为 3 行
- 添加折叠标记 "..." 显示跳过的行
- 优化复制功能包含折叠标记
- 改进视觉效果以匹配 TUI 输出

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Testing Checklist

After implementation, verify:

- [ ] Line numbers in diff start from correct `startLine`
- [ ] Context limited to 3 lines before/after changes
- [ ] "..." markers appear between separated change hunks
- [ ] Stats show correct +/- counts
- [ ] Copy functionality works with collapse markers
- [ ] Syntax highlighting still works
- [ ] No console errors in browser dev tools
