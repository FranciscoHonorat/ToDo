import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import TaskItem from '../src/components/TaskItem.vue'
import type { Task } from '../src/api/types'

const pending: Task = { id: '1', title: 'Comprar pão', description: 'na padaria', status: 'PENDING' }

function mountItem(task: Task = pending, save = vi.fn(async () => true)) {
  return { wrapper: mount(TaskItem, { props: { task, save } }), save }
}

describe('TaskItem', () => {
  it('shows title and description', () => {
    const { wrapper } = mountItem()

    expect(wrapper.text()).toContain('Comprar pão')
    expect(wrapper.text()).toContain('na padaria')
  })

  it('emits complete with the task id', async () => {
    const { wrapper } = mountItem()

    await wrapper.get('[data-test="complete"]').trigger('click')

    expect(wrapper.emitted('complete')).toEqual([['1']])
  })

  it('does not offer complete for a completed task and marks it as done', () => {
    const { wrapper } = mountItem({ ...pending, status: 'COMPLETED' })

    expect(wrapper.find('[data-test="complete"]').exists()).toBe(false)
    expect(wrapper.classes()).toContain('done')
  })

  it('emits remove with the task id', async () => {
    const { wrapper } = mountItem()

    await wrapper.get('[data-test="remove"]').trigger('click')

    expect(wrapper.emitted('remove')).toEqual([['1']])
  })

  it('edit opens a form with the current values and saves with the id', async () => {
    const { wrapper, save } = mountItem()

    await wrapper.get('[data-test="edit"]').trigger('click')
    await wrapper.get('[data-test="title"]').setValue('Comprar leite')
    await wrapper.get('form').trigger('submit')

    expect(save).toHaveBeenCalledWith('1', { title: 'Comprar leite', description: 'na padaria' })
  })

  it('closes the form after a successful save', async () => {
    const { wrapper } = mountItem()

    await wrapper.get('[data-test="edit"]').trigger('click')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('form').exists()).toBe(false)
  })

  it('keeps the form open when save fails', async () => {
    const { wrapper } = mountItem(pending, vi.fn(async () => false))

    await wrapper.get('[data-test="edit"]').trigger('click')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('form').exists()).toBe(true)
  })

  it('cancel closes the form without saving', async () => {
    const { wrapper, save } = mountItem()

    await wrapper.get('[data-test="edit"]').trigger('click')
    await wrapper.get('[data-test="cancel"]').trigger('click')

    expect(wrapper.find('form').exists()).toBe(false)
    expect(save).not.toHaveBeenCalled()
  })
})
