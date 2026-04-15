const NO_SUMMARY_FALLBACK = 'No summary available.'
const TIME_RANGE_MS = {
  '24h': 24 * 60 * 60 * 1000,
  '7d': 7 * 24 * 60 * 60 * 1000,
  '30d': 30 * 24 * 60 * 60 * 1000,
}

function truncateText(text, maxLength) {
  if (text.length <= maxLength) {
    return text
  }

  const truncated = text.slice(0, maxLength).trimEnd()
  return `${truncated}…`
}

function getModifiedTime(plan) {
  return new Date(plan.modified).getTime()
}

function isWithinTimeRange(plan, timeRange, now) {
  if (!timeRange || timeRange === 'all') {
    return true
  }

  const range = TIME_RANGE_MS[timeRange]
  if (!range) {
    return true
  }

  return now - getModifiedTime(plan) <= range
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

  return {
    ...plan,
    content,
    displayTitle,
    summary,
    searchText: `${displayTitle} ${plan.name} ${summary}`.toLowerCase(),
  }
}

export function filterAndSortPlans(plans, { query, sortBy, timeRange, now = Date.now() }) {
  const normalizedQuery = query.trim().toLowerCase()

  return [...plans]
    .filter((plan) => !normalizedQuery || plan.searchText.includes(normalizedQuery))
    .filter((plan) => isWithinTimeRange(plan, timeRange, now))
    .sort((left, right) => {
      if (sortBy === 'name') {
        return left.name.localeCompare(right.name)
      }

      if (sortBy === 'size') {
        return right.size - left.size
      }

      return getModifiedTime(right) - getModifiedTime(left)
    })
}

export function resolveSelectedPlanName(currentName, filteredPlans) {
  if (filteredPlans.some((plan) => plan.name === currentName)) {
    return currentName
  }

  return filteredPlans[0]?.name ?? null
}
