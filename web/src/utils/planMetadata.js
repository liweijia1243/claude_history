const NO_SUMMARY_FALLBACK = 'No summary available.'
const TIME_RANGE_MS = {
  '7d': 7 * 24 * 60 * 60 * 1000,
  '30d': 30 * 24 * 60 * 60 * 1000,
}

function truncateText(text, maxLength) {
  if (text.length <= maxLength) {
    return text
  }

  const truncated = text.slice(0, maxLength).trimEnd()
  const lastSpaceIndex = truncated.lastIndexOf(' ')
  const wordBoundaryText = lastSpaceIndex > 0 ? truncated.slice(0, lastSpaceIndex).trimEnd() : ''

  return `${wordBoundaryText || truncated}…`
}

function normalizeModifiedTime(modified) {
  if (typeof modified === 'number' && Number.isFinite(modified)) {
    return modified < 1e12 ? modified * 1000 : modified
  }

  const parsedTime = new Date(modified).getTime()
  return Number.isNaN(parsedTime) ? null : parsedTime
}

function getModifiedTime(plan) {
  return normalizeModifiedTime(plan.modified)
}

function getComparableName(plan) {
  if (typeof plan.filename === 'string') {
    return plan.filename
  }

  if (typeof plan.name === 'string') {
    return plan.name
  }

  return ''
}

function compareByComparableName(left, right) {
  return getComparableName(left).localeCompare(getComparableName(right))
}

function normalizeQuery(query) {
  if (typeof query === 'string') {
    return query.trim().toLowerCase()
  }

  if (query == null) {
    return ''
  }

  return String(query).trim().toLowerCase()
}

function normalizeSize(size) {
  const normalizedSize = Number(size)
  return Number.isFinite(normalizedSize) ? normalizedSize : Number.NEGATIVE_INFINITY
}

function isWithinTimeRange(plan, timeRange, now) {
  if (!timeRange || timeRange === 'all') {
    return true
  }

  const range = TIME_RANGE_MS[timeRange]
  if (!range) {
    return true
  }

  const modifiedTime = getModifiedTime(plan)
  if (modifiedTime === null || modifiedTime > now) {
    return false
  }

  return now - modifiedTime <= range
}

export function extractPlanTitle(content, fallbackName) {
  const match = content.match(/^#\s+(.+)$/m)
  return match?.[1]?.trim() || fallbackName
}

export function extractPlanSummary(content, maxLength = 160) {
  const summary = content
    .replace(/^#\s+.+$/m, '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1')
    .replace(/^#{2,}\s+/gm, '')
    .replace(/^\s*[-*+]\s+/gm, '')
    .replace(/^\s*\d+\.\s+/gm, '')
    .replace(/^\s*>\s?/gm, '')
    .replace(/\s+/g, ' ')
    .trim()

  if (!summary) {
    return NO_SUMMARY_FALLBACK
  }

  return truncateText(summary, maxLength)
}

export function enrichPlan(plan, content) {
  const displayTitle = extractPlanTitle(content, plan.name)
  const summary = extractPlanSummary(content)
  const searchFilename = plan.filename || plan.name

  return {
    ...plan,
    content,
    displayTitle,
    summary,
    searchText: `${displayTitle} ${searchFilename} ${summary}`.toLowerCase(),
  }
}

export function filterAndSortPlans(plans, { query, sortBy, timeRange, now = Date.now() }) {
  const normalizedQuery = normalizeQuery(query)

  return [...plans]
    .filter((plan) => !normalizedQuery || plan.searchText.includes(normalizedQuery))
    .filter((plan) => isWithinTimeRange(plan, timeRange, now))
    .sort((left, right) => {
      if (sortBy === 'name') {
        return compareByComparableName(left, right)
      }

      if (sortBy === 'size') {
        const sizeDiff = normalizeSize(right.size) - normalizeSize(left.size)
        return sizeDiff || compareByComparableName(left, right)
      }

      const modifiedDiff = (getModifiedTime(right) ?? 0) - (getModifiedTime(left) ?? 0)
      return modifiedDiff || compareByComparableName(left, right)
    })
}

export function resolveSelectedPlanName(currentName, filteredPlans) {
  if (filteredPlans.some((plan) => plan.name === currentName)) {
    return currentName
  }

  return filteredPlans[0]?.name ?? null
}
