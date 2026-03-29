/**
 * ANSI escape sequence handling utilities
 */

// Module-level color constants (avoid recreating on every call)
const STANDARD_COLORS = ['#1e1e1e', '#f87171', '#4ade80', '#fbbf24', '#60a5fa', '#f0abfc', '#22d3ee', '#d4d4d4']
const BRIGHT_COLORS = ['#6b7280', '#fca5a5', '#86efac', '#fde047', '#93c5fd', '#f0abfc', '#67e8f9', '#ffffff']

/**
 * Strip ANSI escape sequences from text
 */
export function stripAnsi(text) {
  if (!text) return ''
  return text.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '')
}

/**
 * Check if text contains terminal-style formatting
 */
export function isTerminalOutput(text) {
  if (!text) return false
  return /\x1b\[([0-9;]*)m/.test(text)
}

/**
 * Convert ANSI color codes to inline CSS
 */
function ansiCodeToStyle(codes) {
  if (!codes || codes === '0' || codes === '') {
    return null
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

    switch (code) {
      case 1: style += 'font-weight:bold;'; break
      case 2: style += 'opacity:0.7;'; break
      case 3: style += 'font-style:italic;'; break
      case 4: style += 'text-decoration:underline;'; break
      default:
        if (code >= 30 && code <= 37) {
          style += `color:${STANDARD_COLORS[code - 30]};`
        } else if (code >= 90 && code <= 97) {
          style += `color:${BRIGHT_COLORS[code - 90]};`
        }
    }
  }

  return style || null
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
 * Wrap text with styled span if style is present
 */
function wrapStyled(text, style) {
  if (!text) return ''
  return style
    ? `<span style="${style}">${escapeHtml(text)}</span>`
    : escapeHtml(text)
}

/**
 * Convert text with ANSI codes to HTML
 */
export function ansiToHtml(text) {
  if (!text) return ''

  const ansiRegex = /\x1b\[([0-9;]*)m/g
  const parts = []
  let lastIndex = 0
  let currentStyle = null

  let match
  while ((match = ansiRegex.exec(text)) !== null) {
    parts.push(wrapStyled(text.slice(lastIndex, match.index), currentStyle))
    currentStyle = ansiCodeToStyle(match[1])
    lastIndex = match.index + match[0].length
  }

  parts.push(wrapStyled(text.slice(lastIndex), currentStyle))
  return parts.join('')
}

/**
 * Process terminal output - wrap in pre with terminal styling
 */
export function processTerminalOutput(text) {
  if (!text) return ''
  const html = ansiToHtml(text)
  return `<pre class="terminal-output">${html}</pre>`
}
