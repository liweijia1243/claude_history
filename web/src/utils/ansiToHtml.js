/**
 * ANSI escape sequence handling utilities
 */

/**
 * Strip ANSI escape sequences from text
 */
export function stripAnsi(text) {
  if (!text) return ''
  return text.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '')
}

/**
 * Check if text contains terminal-style formatting
 * Only returns true for content with ANSI codes (like /context output)
 */
export function isTerminalOutput(text) {
  if (!text) return false
  // Only check for ANSI escape sequences - this is the reliable indicator
  // of terminal-formatted output like /context command results
  return /\x1b\[([0-9;]*)m/.test(text)
}

/**
 * Convert ANSI color codes to inline CSS
 */
function ansiCodeToStyle(codes) {
  if (!codes || codes === '0' || codes === '') {
    return null // Reset
  }

  const parts = codes.split(';').map(Number)
  let style = ''

  for (let i = 0; i < parts.length; i++) {
    const code = parts[i]

    // 24-bit RGB foreground: 38;2;R;G;B
    if (code === 38 && parts[i + 1] === 2) {
      const r = parts[i + 2]
      const g = parts[i + 3]
      const b = parts[i + 4]
      if (r !== undefined && g !== undefined && b !== undefined) {
        style += `color:rgb(${r},${g},${b});`
        i += 4
        continue
      }
    }

    // 24-bit RGB background: 48;2;R;G;B
    if (code === 48 && parts[i + 1] === 2) {
      const r = parts[i + 2]
      const g = parts[i + 3]
      const b = parts[i + 4]
      if (r !== undefined && g !== undefined && b !== undefined) {
        style += `background-color:rgb(${r},${g},${b});`
        i += 4
        continue
      }
    }

    // Standard codes
    switch (code) {
      case 1: style += 'font-weight:bold;'; break
      case 2: style += 'opacity:0.7;'; break
      case 3: style += 'font-style:italic;'; break
      case 4: style += 'text-decoration:underline;'; break
      default:
        if (code >= 30 && code <= 37) {
          const colors = ['#1e1e1e', '#f87171', '#4ade80', '#fbbf24', '#60a5fa', '#f0abfc', '#22d3ee', '#d4d4d4']
          style += `color:${colors[code - 30]};`
        } else if (code >= 90 && code <= 97) {
          const colors = ['#6b7280', '#fca5a5', '#86efac', '#fde047', '#93c5fd', '#f0abfc', '#67e8f9', '#ffffff']
          style += `color:${colors[code - 90]};`
        }
    }
  }

  return style || null
}

/**
 * Convert text with ANSI codes to HTML
 */
export function ansiToHtml(text) {
  if (!text) return ''

  const ansiRegex = /\x1b\[([0-9;]*)m/g
  let result = ''
  let lastIndex = 0
  let currentStyle = null

  let match
  while ((match = ansiRegex.exec(text)) !== null) {
    // Add text chunk
    const chunk = text.slice(lastIndex, match.index)
    if (chunk) {
      if (currentStyle) {
        result += `<span style="${currentStyle}">${escapeHtml(chunk)}</span>`
      } else {
        result += escapeHtml(chunk)
      }
    }

    // Update style
    const newStyle = ansiCodeToStyle(match[1])
    currentStyle = newStyle
    lastIndex = match.index + match[0].length
  }

  // Add remaining text
  const remaining = text.slice(lastIndex)
  if (remaining) {
    if (currentStyle) {
      result += `<span style="${currentStyle}">${escapeHtml(remaining)}</span>`
    } else {
      result += escapeHtml(remaining)
    }
  }

  return result
}

/**
 * Escape HTML special characters
 */
function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

/**
 * Process terminal output - wrap in pre with terminal styling
 */
export function processTerminalOutput(text) {
  if (!text) return ''
  const html = ansiToHtml(text)
  return `<pre class="terminal-output">${html}</pre>`
}
