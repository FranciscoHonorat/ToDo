import { afterEach, describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import App from '../src/App.vue'
import { FakeTaskApi } from './fakeTaskApi'

async function mountApp(api = new FakeTaskApi(), pageSize?: number) {
  const wrapper = mount(App, { props: { api, pageSize } })
  await flushPromises()
  return { wrapper, api }
}

async function addTask(wrapper: Awaited<ReturnType<typeof mountApp>>['wrapper'], title: string) {
  await wrapper.get('[data-test="new-task"] [data-test="title"]').setValue(title)
  await wrapper.get('[data-test="new-task"] form').trigger('submit')
  await flushPromises()
}

describe('App', () => {
  afterEach(() => history.replaceState(null, '', '/'))

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

  it('a blank title is caught on the field, without calling the backend', async () => {
    const { wrapper } = await mountApp()

    await addTask(wrapper, '   ')

    expect(wrapper.get('[data-test="title-error"]').text()).toBe('Dê um título para a tarefa.')
    expect(wrapper.find('[data-test="empty"]').exists()).toBe(true)
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

  it('offers undo after removing a task and restores it', async () => {
    const { wrapper } = await mountApp()
    await addTask(wrapper, 'Sem querer')

    await wrapper.get('[data-test="remove"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-test="toast"]').text()).toContain('Sem querer')

    await wrapper.get('[data-test="undo"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Sem querer')
    expect(wrapper.find('[data-test="toast"]').exists()).toBe(false)
  })

  it('the error can be dismissed', async () => {
    const api = new FakeTaskApi()
    api.create = async () => {
      throw new TypeError('Failed to fetch')
    }
    const { wrapper } = await mountApp(api)
    await addTask(wrapper, 'Sem rede')
    expect(wrapper.get('[role="alert"]').text()).toContain('Não foi possível falar com o servidor')

    await wrapper.get('[data-test="dismiss-error"]').trigger('click')

    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })

  it('the empty message reflects the active filter', async () => {
    const { wrapper } = await mountApp()

    await wrapper.get('[data-test="filter-completed"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-test="empty"]').text()).toBe('Nenhuma tarefa concluída.')
  })

  it('shows the progress of completed tasks', async () => {
    const { wrapper } = await mountApp()
    await addTask(wrapper, 'A')
    await addTask(wrapper, 'B')
    expect(wrapper.get('[data-test="progress"]').text()).toBe('0 de 2 concluídas')

    await wrapper.findAll('[data-test="complete"]')[0].trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-test="progress"]').text()).toBe('1 de 2 concluídas')
    expect(wrapper.get('[role="progressbar"]').attributes('aria-valuenow')).toBe('50')
  })

  it('celebrates when nothing is pending', async () => {
    const { wrapper } = await mountApp()
    await addTask(wrapper, 'A')
    await wrapper.get('[data-test="complete"]').trigger('click')
    await flushPromises()

    await wrapper.get('[data-test="filter-pending"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-test="empty"]').text()).toBe('Tudo em dia!')
  })

  it('shows a loading state before the first load finishes', async () => {
    const wrapper = mount(App, { props: { api: new FakeTaskApi() } })

    expect(wrapper.find('[data-test="loading"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="empty"]').exists()).toBe(false)

    await flushPromises()
    expect(wrapper.find('[data-test="loading"]').exists()).toBe(false)
  })

  it('reopens a completed task by clicking its check', async () => {
    const { wrapper } = await mountApp()
    await addTask(wrapper, 'A')
    await wrapper.get('[data-test="complete"]').trigger('click')
    await flushPromises()

    await wrapper.get('[data-test="reopen"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="complete"]').exists()).toBe(true)
  })

  it('shows "Carregar mais" while there are more tasks and the count uses the total', async () => {
    const api = new FakeTaskApi()
    for (const title of ['A', 'B', 'C']) await api.create({ title, description: '' })
    const { wrapper } = await mountApp(api, 2)

    expect(wrapper.findAll('[data-test="task"]')).toHaveLength(2)
    expect(wrapper.get('[data-test="filter-all"]').text()).toBe('Todas 3')

    await wrapper.get('[data-test="load-more"]').trigger('click')
    await flushPromises()

    expect(wrapper.findAll('[data-test="task"]')).toHaveLength(3)
    expect(wrapper.find('[data-test="load-more"]').exists()).toBe(false)
  })

  it('reads the filter from the URL and keeps the URL in sync', async () => {
    history.replaceState(null, '', '/?status=completed')
    const { wrapper } = await mountApp()

    expect(wrapper.get('[data-test="filter-completed"]').attributes('aria-pressed')).toBe('true')

    await wrapper.get('[data-test="filter-pending"]').trigger('click')
    await flushPromises()
    expect(location.search).toBe('?status=pending')

    await wrapper.get('[data-test="filter-all"]').trigger('click')
    await flushPromises()
    expect(location.search).toBe('')
  })

  it('ignores an unknown status in the URL', async () => {
    history.replaceState(null, '', '/?status=whatever')
    const { wrapper } = await mountApp()

    expect(wrapper.get('[data-test="filter-all"]').attributes('aria-pressed')).toBe('true')
  })
})
