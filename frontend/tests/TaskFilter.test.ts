import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import TaskFilter from '../src/components/TaskFilter.vue'

describe('TaskFilter', () => {
  it('marks the current filter as pressed', () => {
    const wrapper = mount(TaskFilter, { props: { modelValue: 'pending' } })

    expect(wrapper.get('[data-test="filter-pending"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('[data-test="filter-all"]').attributes('aria-pressed')).toBe('false')
  })

  it.each([
    ['all', undefined],
    ['pending', 'pending'],
    ['completed', 'completed'],
  ])('clicking %s emits update:modelValue with %s', async (name, value) => {
    const wrapper = mount(TaskFilter, { props: { modelValue: undefined } })

    await wrapper.get(`[data-test="filter-${name}"]`).trigger('click')

    expect(wrapper.emitted('update:modelValue')).toEqual([[value]])
  })
})
