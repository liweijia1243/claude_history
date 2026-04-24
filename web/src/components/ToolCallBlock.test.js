import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import ToolCallBlock from './ToolCallBlock.vue'

describe('ToolCallBlock Codex tools', () => {
  it('renders exec_command as terminal output with exit code metadata', async () => {
    const wrapper = mount(ToolCallBlock, {
      props: {
        toolUses: [
          {
            id: 'call-1',
            name: 'exec_command',
            input: { command: ['pwd'], cwd: '/repo/alpha' },
            metadata: { provider: 'codex' },
          },
        ],
        toolResults: [
          {
            tool_use_id: 'call-1',
            content: 'command output\n',
            is_error: false,
            metadata: { exit_code: 0, cwd: '/repo/alpha', command: ['pwd'] },
          },
        ],
      },
    })

    expect(wrapper.text()).toContain('exec_command')
    expect(wrapper.text()).toContain('pwd')

    await wrapper.get('button').trigger('click')

    expect(wrapper.text()).toContain('exit 0')
    expect(wrapper.text()).toContain('/repo/alpha')
    expect(wrapper.text()).toContain('command output')
  })

  it('keeps unknown tools visible through fallback json rendering', async () => {
    const wrapper = mount(ToolCallBlock, {
      props: {
        toolUses: [{ id: 'call-2', name: 'mcp_custom_tool', input: { value: 42 } }],
        toolResults: [],
      },
    })

    await wrapper.get('button').trigger('click')

    expect(wrapper.text()).toContain('mcp_custom_tool')
    expect(wrapper.text()).toContain('"value": 42')
  })
})
