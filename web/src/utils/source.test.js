import { describe, expect, it } from 'vitest'

import { apiPath, routePath, sourceFromRoute } from './source'

describe('sourceFromRoute', () => {
  it('defaults old routes to claude', () => {
    expect(sourceFromRoute({ path: '/projects' })).toBe('claude')
    expect(sourceFromRoute({ params: {} })).toBe('claude')
  })

  it('reads route.params.source', () => {
    expect(sourceFromRoute({ params: { source: 'codex' } })).toBe('codex')
  })
})

describe('apiPath', () => {
  it('builds /api/{source}/... paths', () => {
    expect(apiPath('codex', 'projects')).toBe('/api/codex/projects')
    expect(apiPath('codex', '/projects')).toBe('/api/codex/projects')
  })

  it('defaults missing sources to claude', () => {
    expect(apiPath(undefined, '/projects')).toBe('/api/claude/projects')
    expect(apiPath('', '/projects')).toBe('/api/claude/projects')
  })
})

describe('routePath', () => {
  it('returns legacy paths for claude/default sources', () => {
    expect(routePath('claude', 'projects')).toBe('/projects')
    expect(routePath(undefined, '/projects')).toBe('/projects')
  })

  it('returns /sources/{source}/... paths for codex', () => {
    expect(routePath('codex', 'projects')).toBe('/sources/codex/projects')
    expect(routePath('codex', '/projects')).toBe('/sources/codex/projects')
    expect(routePath('codex', '')).toBe('/sources/codex')
  })

  it('keeps plans as a legacy claude-only path', () => {
    expect(routePath('codex', '/plans')).toBe('/plans')
    expect(routePath('codex', 'plans')).toBe('/plans')
  })
})
