import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import PlansView from './PlansView.vue'

const plansResponse = [
  {
    name: 'alpha',
    size: 1200,
    modified: 1713096000,
  },
  {
    name: 'beta',
    size: 800,
    modified: 1713182400,
  },
]

const planDetails = {
  alpha: {
    content: '# Alpha Plan\n\nAlpha preview content.',
  },
  beta: {
    content: '# Beta Plan\n\nBeta preview content.',
  },
}

function createFetchMock() {
  return vi.fn((url) => {
    if (url === '/api/plans') {
      return Promise.resolve({
        json: () => Promise.resolve(plansResponse),
      })
    }

    if (url === '/api/plans/alpha') {
      return Promise.resolve({
        json: () => Promise.resolve(planDetails.alpha),
      })
    }

    if (url === '/api/plans/beta') {
      return Promise.resolve({
        json: () => Promise.resolve(planDetails.beta),
      })
    }

    return Promise.reject(new Error(`Unexpected fetch URL: ${url}`))
  })
}

describe('PlansView', () => {
  beforeEach(() => {
    global.fetch = createFetchMock()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('loads plan details and defaults to the first filtered preview', async () => {
    const wrapper = mount(PlansView)

    await flushPromises()

    expect(global.fetch).toHaveBeenCalledWith('/api/plans')
    expect(global.fetch).toHaveBeenCalledWith('/api/plans/alpha')
    expect(global.fetch).toHaveBeenCalledWith('/api/plans/beta')
    expect(wrapper.html()).toContain('<h1>Beta Plan</h1>')
    expect(wrapper.text()).toContain('Beta preview content.')
    expect(wrapper.text()).toContain('alpha')
    expect(wrapper.text()).toContain('beta')
  })

  it('loads the filtered plan preview when searching by plan name', async () => {
    const wrapper = mount(PlansView)

    await flushPromises()

    const searchInput = wrapper.get('input[type="search"]')
    await searchInput.setValue('beta')
    await flushPromises()

    expect(global.fetch).toHaveBeenCalledWith('/api/plans')
    expect(global.fetch).toHaveBeenCalledWith('/api/plans/beta')
    expect(wrapper.html()).toContain('<h1>Beta Plan</h1>')
    expect(wrapper.text()).toContain('Beta preview content.')
  })

  it('switches preview when the selected plan is filtered out', async () => {
    const wrapper = mount(PlansView)

    await flushPromises()

    const betaButton = wrapper.get('button[title="beta"]')
    await betaButton.trigger('click')
    await flushPromises()

    expect(global.fetch).toHaveBeenCalledWith('/api/plans/beta')
    expect(wrapper.text()).toContain('Beta preview content.')

    const searchInput = wrapper.get('input[type="search"]')
    await searchInput.setValue('alpha')
    await flushPromises()

    expect(wrapper.html()).toContain('<h1>Alpha Plan</h1>')
    expect(wrapper.text()).toContain('Alpha preview content.')
  })

  it('does not keep showing the previously selected preview after filtering it out', async () => {
    const wrapper = mount(PlansView)

    await flushPromises()

    const betaButton = wrapper.get('button[title="beta"]')
    await betaButton.trigger('click')
    await flushPromises()

    const searchInput = wrapper.get('input[type="search"]')
    await searchInput.setValue('alpha')
    await flushPromises()

    expect(wrapper.find('.plan-preview').text()).not.toContain('Beta preview content.')
  })

  it('shows empty state when no plan matches filters', async () => {
    const wrapper = mount(PlansView)

    await flushPromises()

    const searchInput = wrapper.get('input[type="search"]')
    await searchInput.setValue('missing')
    await flushPromises()

    expect(wrapper.text()).toContain('No plans match the current filters.')
    expect(wrapper.text()).not.toContain('Alpha preview content.')
    expect(wrapper.text()).not.toContain('Beta preview content.')
  })
})
