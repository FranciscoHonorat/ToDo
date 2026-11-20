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

  it('shows a count next to each option when counts are given', () => {
    const wrapper = mount(TaskFilter, {
      props: { modelValue: undefined, counts: { all: 7, pending: 4, completed: 3 } },
    })

    expect(wrapper.get('[data-test="filter-all"]').text()).toBe('Todas 7')
    expect(wrapper.get('[data-test="filter-pending"]').text()).toBe('Pendentes 4')
    expect(wrapper.get('[data-test="filter-completed"]').text()).toBe('Concluídas 3')
  })
})
