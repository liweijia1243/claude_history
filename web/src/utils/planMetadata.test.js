import { describe, expect, it } from 'vitest'

import {
  enrichPlan,
  extractPlanSummary,
  extractPlanTitle,
  filterAndSortPlans,
  resolveSelectedPlanName,
} from './planMetadata'

describe('extractPlanTitle', () => {
  it('uses markdown H1 when present', () => {
    expect(extractPlanTitle('# My Plan\n\nBody', 'fallback.md')).toBe('My Plan')
  })

  it('falls back to filename when H1 is missing', () => {
    expect(extractPlanTitle('## Subtitle\n\nBody', 'fallback.md')).toBe('fallback.md')
  })
})

describe('extractPlanSummary', () => {
  it('removes H1 code fences inline code and markdown links', () => {
    const content = [
      '# My Plan',
      '',
      'This is a [linked summary](https://example.com) with `inline code`.',
      '',
      '```js',
      'const hidden = true',
      '```',
      '',
      'More details here.',
    ].join('\n')

    expect(extractPlanSummary(content)).toBe(
      'This is a linked summary with inline code. More details here.'
    )
  })

  it('strips common markdown structure markers from summaries', () => {
    const content = [
      '# Launch Plan',
      '',
      '## Milestones',
      '- First item',
      '1. Second item',
      '> Final note',
    ].join('\n')

    expect(extractPlanSummary(content)).toBe('Milestones First item Second item Final note')
  })

  it('truncates at a word boundary when possible', () => {
    expect(extractPlanSummary('Alpha beta gamma delta', 13)).toBe('Alpha beta…')
  })

  it('returns fallback when no summary content remains', () => {
    expect(extractPlanSummary('# Title\n\n```js\nconst x = 1\n```')).toBe('No summary available.')
  })
})

describe('enrichPlan', () => {
  it('attaches derived metadata fields using filename in search text', () => {
    const plan = {
      name: 'display-only.md',
      filename: 'plan-a.md',
      size: 42,
      modified: '2026-04-10T12:00:00.000Z',
    }
    const content = '# Launch Plan\n\nPrepare rollout checklist.'

    expect(enrichPlan(plan, content)).toEqual({
      ...plan,
      content,
      displayTitle: 'Launch Plan',
      summary: 'Prepare rollout checklist.',
      searchText: 'launch plan plan-a.md prepare rollout checklist.',
    })
  })
})

describe('filterAndSortPlans', () => {
  const now = new Date('2026-04-15T12:00:00.000Z').getTime()
  const plans = [
    {
      name: 'zeta.md',
      size: 400,
      modified: '2026-04-14T12:00:00.000Z',
      searchText: 'zeta latest release notes',
    },
    {
      name: 'alpha.md',
      size: 100,
      modified: '2026-04-15T09:00:00.000Z',
      searchText: 'alpha onboarding checklist',
    },
    {
      name: 'beta.md',
      size: 250,
      modified: '2026-03-01T12:00:00.000Z',
      searchText: 'beta migration guide',
    },
  ]

  const backendPlans = [
    {
      name: 'old.md',
      size: 10,
      modified: 1713096000,
      searchText: 'old backend plan',
    },
    {
      name: 'latest.md',
      size: 20,
      modified: 1713182400,
      searchText: 'latest backend plan',
    },
    {
      name: 'invalid.md',
      size: 5,
      modified: 'not-a-date',
      searchText: 'invalid backend plan',
    },
  ]

  it('filters by query and sorts by modified descending', () => {
    expect(
      filterAndSortPlans(plans, { query: 'checklist', sortBy: 'modified', timeRange: 'all', now })
    ).toEqual([plans[1]])
  })

  it('filters by recent time range', () => {
    expect(
      filterAndSortPlans(plans, { query: '', sortBy: 'modified', timeRange: '7d', now })
    ).toEqual([plans[1], plans[0]])
  })

  it('sorts by name ascending', () => {
    expect(filterAndSortPlans(plans, { query: '', sortBy: 'name', timeRange: 'all', now })).toEqual([
      plans[1],
      plans[2],
      plans[0],
    ])
  })

  it('sorts backend seconds-based modified values in descending order', () => {
    expect(
      filterAndSortPlans(backendPlans, { query: '', sortBy: 'modified', timeRange: 'all', now })
    ).toEqual([backendPlans[1], backendPlans[0], backendPlans[2]])
  })

  it('filters backend seconds-based modified values by time range', () => {
    expect(
      filterAndSortPlans(backendPlans, {
        query: '',
        sortBy: 'modified',
        timeRange: '24h',
        now: new Date('2024-04-15T12:00:00.000Z').getTime(),
      })
    ).toEqual([backendPlans[1], backendPlans[0]])
  })

  it('excludes invalid modified values from bounded recency filters', () => {
    expect(
      filterAndSortPlans(backendPlans, {
        query: '',
        sortBy: 'modified',
        timeRange: '7d',
        now: new Date('2024-04-16T12:00:00.000Z').getTime(),
      })
    ).toEqual([backendPlans[1], backendPlans[0]])
  })

  it('keeps invalid modified values from crashing filtering and sorts them last for all time', () => {
    expect(() =>
      filterAndSortPlans(backendPlans, { query: '', sortBy: 'modified', timeRange: 'all', now })
    ).not.toThrow()

    expect(
      filterAndSortPlans(backendPlans, { query: '', sortBy: 'modified', timeRange: 'all', now })
    ).toEqual([backendPlans[1], backendPlans[0], backendPlans[2]])
  })

  it('uses a deterministic tie-breaker when modified timestamps normalize equally', () => {
    const tiedModifiedPlans = [
      {
        name: 'zeta.md',
        filename: 'zeta.md',
        size: 10,
        modified: '2026-04-15T09:00:00.000Z',
        searchText: 'zeta plan',
      },
      {
        name: 'alpha.md',
        filename: 'alpha.md',
        size: 20,
        modified: 1776243600,
        searchText: 'alpha plan',
      },
    ]

    expect(
      filterAndSortPlans(tiedModifiedPlans, {
        query: '',
        sortBy: 'modified',
        timeRange: 'all',
        now,
      })
    ).toEqual([tiedModifiedPlans[1], tiedModifiedPlans[0]])
  })

  it('sorts by name defensively and deterministically when names are missing or invalid', () => {
    const mixedNamePlans = [
      {
        filename: 'beta.md',
        name: null,
        size: 10,
        modified: '2026-04-10T12:00:00.000Z',
        searchText: 'beta plan',
      },
      {
        filename: 'alpha.md',
        name: 42,
        size: 10,
        modified: '2026-04-10T12:00:00.000Z',
        searchText: 'alpha plan',
      },
      {
        filename: 'gamma.md',
        name: 'gamma.md',
        size: 10,
        modified: '2026-04-10T12:00:00.000Z',
        searchText: 'gamma plan',
      },
    ]

    expect(() =>
      filterAndSortPlans(mixedNamePlans, { query: '', sortBy: 'name', timeRange: 'all', now })
    ).not.toThrow()

    expect(
      filterAndSortPlans(mixedNamePlans, { query: '', sortBy: 'name', timeRange: 'all', now })
    ).toEqual([mixedNamePlans[1], mixedNamePlans[0], mixedNamePlans[2]])
  })

  it('sorts by size descending', () => {
    expect(filterAndSortPlans(plans, { query: '', sortBy: 'size', timeRange: 'all', now })).toEqual([
      plans[0],
      plans[2],
      plans[1],
    ])
  })
})

describe('resolveSelectedPlanName', () => {
  const filteredPlans = [{ name: 'alpha.md' }, { name: 'beta.md' }]

  it('keeps the current selection when still present', () => {
    expect(resolveSelectedPlanName('beta.md', filteredPlans)).toBe('beta.md')
  })

  it('falls back to the first filtered plan when current selection is missing', () => {
    expect(resolveSelectedPlanName('missing.md', filteredPlans)).toBe('alpha.md')
  })

  it('returns null when no plans remain', () => {
    expect(resolveSelectedPlanName('alpha.md', [])).toBeNull()
  })
})
