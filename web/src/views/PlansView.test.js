import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import PlansView from './PlansView.vue'

const plansResponse = [
  {
    name: 'alpha',
    filename: 'alpha.md',
    size: 1200,
    modified: 1713096000,
  },
  {
    name: 'beta',
    filename: 'beta.md',
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

  it('defaults preview to the first plan in the filtered and modified-desc sorted list', async () => {
    const wrapper = mount(PlansView)

    await flushPromises()

    expect(global.fetch).toHaveBeenCalledWith('/api/plans')
    expect(global.fetch).toHaveBeenCalledWith('/api/plans/alpha')
    expect(global.fetch).toHaveBeenCalledWith('/api/plans/beta')
    expect(wrapper.find('.plan-preview').html()).toContain('<h1>Beta Plan</h1>')
    expect(wrapper.find('.plan-preview').text()).toContain('Beta preview content.')
    expect(wrapper.text()).toContain('alpha.md')
    expect(wrapper.text()).toContain('beta.md')
    expect(wrapper.find('button[title="beta"]').classes()).toContain('border-blue-500')
    expect(wrapper.find('button[title="alpha"]').classes()).not.toContain('border-blue-500')
    expect(wrapper.text()).toContain('beta.md')
  })

  it('keeps the remaining filtered plan active across list and preview columns', async () => {
    const wrapper = mount(PlansView)

    await flushPromises()

    const searchInput = wrapper.get('input[type="search"]')
    await searchInput.setValue('beta')
    await flushPromises()

    expect(global.fetch).toHaveBeenCalledWith('/api/plans')
    expect(global.fetch).toHaveBeenCalledWith('/api/plans/beta')
    expect(wrapper.findAll('button[title]').map((button) => button.attributes('title'))).toEqual(['beta'])
    expect(wrapper.find('button[title="beta"]').classes()).toContain('border-blue-500')
    expect(wrapper.find('.plan-preview').html()).toContain('<h1>Beta Plan</h1>')
    expect(wrapper.find('.plan-preview').text()).toContain('Beta preview content.')
    expect(wrapper.text()).toContain('beta.md')
  })

  it('switches the active card and preview when filtering removes the current selection', async () => {
    const wrapper = mount(PlansView)

    await flushPromises()

    const betaButton = wrapper.get('button[title="beta"]')
    await betaButton.trigger('click')
    await flushPromises()

    expect(global.fetch).toHaveBeenCalledWith('/api/plans/beta')
    expect(wrapper.find('button[title="beta"]').classes()).toContain('border-blue-500')
    expect(wrapper.find('.plan-preview').text()).toContain('Beta preview content.')

    const searchInput = wrapper.get('input[type="search"]')
    await searchInput.setValue('alpha')
    await flushPromises()

    expect(wrapper.findAll('button[title]').map((button) => button.attributes('title'))).toEqual(['alpha'])
    expect(wrapper.find('button[title="alpha"]').classes()).toContain('border-blue-500')
    expect(wrapper.find('.plan-preview').html()).toContain('<h1>Alpha Plan</h1>')
    expect(wrapper.find('.plan-preview').text()).toContain('Alpha preview content.')
    expect(wrapper.text()).toContain('alpha.md')
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

  it('shows list and preview empty states when no plan matches filters', async () => {
    const wrapper = mount(PlansView)

    await flushPromises()

    const searchInput = wrapper.get('input[type="search"]')
    await searchInput.setValue('missing')
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('No plans match the current filters.')
    expect(text).toContain('Select a plan from the list to preview its content.')
    expect(text).not.toContain('Alpha preview content.')
    expect(text).not.toContain('Beta preview content.')
  })
})
