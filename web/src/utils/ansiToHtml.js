/**
 * Convert ANSI escape sequences to HTML spans with CSS classes
 * or strip them entirely for plain text display.
 */

// ANSI color codes mapped to CSS classes
const ansiColors = {
  // Foreground colors (30-37, 90-97)
  30: 'ansi-black',
  31: 'ansi-red',
  32: 'ansi-green',
  33: 'ansi-yellow',
  34: 'ansi-blue',
  35: 'ansi-magenta',
  36: 'ansi-cyan',
  37: 'ansi-white',
  90: 'ansi-bright-black',
  91: 'ansi-bright-red',
  92: 'ansi-bright-green',
  93: 'ansi-bright-yellow',
  94: 'ansi-bright-blue',
  95: 'ansi-bright-magenta',
  96: 'ansi-bright-cyan',
  97: 'ansi-bright-white',
  // Background colors (40-47, 100-107)
  40: 'ansi-bg-black',
  41: 'ansi-bg-red',
  42: 'ansi-bg-green',
  43: 'ansi-bg-yellow',
  44: 'ansi-bg-blue',
  45: 'ansi-bg-magenta',
  46: 'ansi-bg-cyan',
  47: 'ansi-bg-white',
  100: 'ansi-bg-bright-black',
  101: 'ansi-bg-bright-red',
  102: 'ansi-bg-bright-green',
  103: 'ansi-bg-bright-yellow',
  104: 'ansi-bg-bright-blue',
  105: 'ansi-bg-magenta',
  106: 'ansi-bg-bright-cyan',
  107: 'ansi-bg-bright-white',
}

// Styles
const ansiStyles = {
  1: 'ansi-bold',
  2: 'ansi-dim',
  3: 'ansi-italic',
  4: 'ansi-underline',
  7: 'ansi-inverse',
  22: 'ansi-normal',
  23: 'ansi-no-italic',
  24: 'ansi-no-underline',
}

/**
 * Parse ANSI escape sequence and return CSS classes
 */
function parseAnsiCode(code) {
  const parts = code.split(';').map(Number)
  const classes = []

  for (const part of parts) {
    if (ansiColors[part]) {
      classes.push(ansiColors[part])
    } else if (ansiStyles[part]) {
      classes.push(ansiStyles[part])
    }
  }

  return classes.join(' ')
}

/**
 * Convert text with ANSI escape sequences to HTML
 */
export function ansiToHtml(text) {
  if (!text) return ''

  // Match ANSI escape sequences: ESC[ ... m
  const ansiRegex = /\x1b\[([0-9;]*)m/g

  let result = ''
  let lastIndex = 0
  const openTags = []

  text = text.replace(ansiRegex, (match, code) => {
    const classes = parseAnsiCode(code)
    if (classes) {
      return `</span><span class="${classes}">`
    }
    return '' // Reset code (0 or empty)
  })

  // Wrap in a container span and clean up empty tags
  text = text.replace(/<\/span><span/g, '<span').replace(/^<span class="([^"]*)"><\/span>/, '')

  // If no ANSI sequences were found, return original
  if (!text.includes('class="ansi-')) {
    return escapeHtml(text.replace(/<\/span><span/g, ''))
  }

  return `<span class="ansi-output">${text}</span>`
}

/**
 * Strip ANSI escape sequences from text
 */
export function stripAnsi(text) {
  if (!text) return ''
  return text.replace(/\x1b\[[0-9;]*m/g, '')
}

/**
 * Escape HTML special characters
 */
function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

/**
 * Process text: convert ANSI to HTML if present, otherwise escape HTML
 */
export function processText(text) {
  if (!text) return ''

  // Check if text contains ANSI sequences
  if (/\x1b\[[0-9;]*m/.test(text)) {
    return ansiToHtml(text)
  }

  return escapeHtml(text)
}
