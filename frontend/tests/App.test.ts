import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import App from '../src/App.vue'
import { FakeTaskApi } from './fakeTaskApi'

async function mountApp(api = new FakeTaskApi()) {
  const wrapper = mount(App, { props: { api } })
  await flushPromises()
  return { wrapper, api }
}

async function addTask(wrapper: Awaited<ReturnType<typeof mountApp>>['wrapper'], title: string) {
  await wrapper.get('[data-test="new-task"] [data-test="title"]').setValue(title)
  await wrapper.get('[data-test="new-task"] form').trigger('submit')
  await flushPromises()
}

describe('App', () => {
  it('loads existing tasks on mount', async () => {
    const api = new FakeTaskApi()
    await api.create({ title: 'Já existia', description: '' })

    const { wrapper } = await mountApp(api)

    expect(wrapper.text()).toContain('Já existia')
  })

  it('shows an empty message when there are no tasks', async () => {
    const { wrapper } = await mountApp()

    expect(wrapper.get('[data-test="empty"]').text()).toBe('Nenhuma tarefa.')
  })

  it('adds a task through the form', async () => {
    const { wrapper } = await mountApp()

    await addTask(wrapper, 'Comprar pão')

    expect(wrapper.findAll('[data-test="task"]')).toHaveLength(1)
    expect(wrapper.text()).toContain('Comprar pão')
  })

  it('shows the backend error for a blank title', async () => {
    const { wrapper } = await mountApp()

    await addTask(wrapper, '   ')

    expect(wrapper.get('[role="alert"]').text()).toBe('Title cannot be empty.')
  })

  it('completes, filters and removes tasks end to end', async () => {
    const { wrapper } = await mountApp()
    await addTask(wrapper, 'A')
    await addTask(wrapper, 'B')

    await wrapper.findAll('[data-test="complete"]')[0].trigger('click')
    await flushPromises()
    await wrapper.get('[data-test="filter-pending"]').trigger('click')
    await flushPromises()

    expect(wrapper.findAll('[data-test="task"]').map((t) => t.text())).toEqual([expect.stringContaining('B')])

    await wrapper.get('[data-test="remove"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="empty"]').exists()).toBe(true)
  })
})
