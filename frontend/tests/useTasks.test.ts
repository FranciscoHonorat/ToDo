import { beforeEach, describe, expect, it } from 'vitest'
import { useTasks } from '../src/composables/useTasks'
import { ApiError } from '../src/api/types'
import { FakeTaskApi } from './fakeTaskApi'

describe('useTasks', () => {
  let api: FakeTaskApi
  let store: ReturnType<typeof useTasks>

  beforeEach(() => {
    api = new FakeTaskApi()
    store = useTasks(api)
  })

  it('starts with an empty list and no error', () => {
    expect(store.tasks.value).toEqual([])
    expect(store.error.value).toBeNull()
  })

  it('load fetches tasks from the api', async () => {
    await api.create({ title: 'A', description: '' })

    await store.load()

    expect(store.tasks.value.map((t) => t.title)).toEqual(['A'])
  })

  it('create adds the task and returns true', async () => {
    const ok = await store.create({ title: 'A', description: '' })

    expect(ok).toBe(true)
    expect(store.tasks.value.map((t) => t.title)).toEqual(['A'])
  })

  it('create with blank title sets error and returns false', async () => {
    const ok = await store.create({ title: ' ', description: '' })

    expect(ok).toBe(false)
    expect(store.error.value).toBe('Dê um título para a tarefa.')
    expect(store.tasks.value).toEqual([])
  })

  it('a successful action clears the previous error', async () => {
    await store.create({ title: ' ', description: '' })

    await store.create({ title: 'A', description: '' })

    expect(store.error.value).toBeNull()
  })

  it('edit changes the task', async () => {
    await store.create({ title: 'A', description: '' })
    const id = store.tasks.value[0].id

    const ok = await store.edit(id, { title: 'B', description: 'b' })

    expect(ok).toBe(true)
    expect(store.tasks.value[0]).toMatchObject({ title: 'B', description: 'b' })
  })

  it('complete marks the task as completed', async () => {
    await store.create({ title: 'A', description: '' })

    await store.complete(store.tasks.value[0].id)

    expect(store.tasks.value[0].status).toBe('COMPLETED')
  })

  it('remove deletes the task', async () => {
    await store.create({ title: 'A', description: '' })

    await store.remove(store.tasks.value[0].id)

    expect(store.tasks.value).toEqual([])
  })

  it('remove with unknown id sets the error', async () => {
    await store.remove('nope')

    expect(store.error.value).toBe('Essa tarefa não existe mais. A lista foi atualizada.')
  })

  it('setFilter reloads only tasks with that status', async () => {
    await store.create({ title: 'Pending', description: '' })
    await store.create({ title: 'Done', description: '' })
    await store.complete(store.tasks.value[1].id)

    await store.setFilter('completed')

    expect(store.filter.value).toBe('completed')
    expect(store.tasks.value.map((t) => t.title)).toEqual(['Done'])
  })

  it('completing a task while filtering pending removes it from the list', async () => {
    await store.create({ title: 'A', description: '' })
    await store.setFilter('pending')

    await store.complete(store.tasks.value[0].id)

    expect(store.tasks.value).toEqual([])
  })

  it('loading starts true (nothing loaded yet) and becomes false after load', async () => {
    expect(store.loading.value).toBe(true)
    const pending = store.load()

    expect(store.loading.value).toBe(true)
    await pending
    expect(store.loading.value).toBe(false)
  })

  it('dismissError clears the error', async () => {
    await store.create({ title: ' ', description: '' })

    store.dismissError()

    expect(store.error.value).toBeNull()
  })

  it('remove remembers the removed task so it can be undone', async () => {
    await store.create({ title: 'A', description: 'a' })

    await store.remove(store.tasks.value[0].id)

    expect(store.removed.value).toMatchObject({ title: 'A', description: 'a' })
  })

  it('undoRemove recreates the removed task and forgets it', async () => {
    await store.create({ title: 'A', description: 'a' })
    await store.remove(store.tasks.value[0].id)

    const ok = await store.undoRemove()

    expect(ok).toBe(true)
    expect(store.tasks.value).toEqual([expect.objectContaining({ title: 'A', description: 'a', status: 'PENDING' })])
    expect(store.removed.value).toBeNull()
  })

  it('undoRemove keeps a completed task completed', async () => {
    await store.create({ title: 'A', description: '' })
    await store.complete(store.tasks.value[0].id)
    await store.remove(store.tasks.value[0].id)

    await store.undoRemove()

    expect(store.tasks.value[0].status).toBe('COMPLETED')
  })

  it('forgetRemoved drops the undo option', async () => {
    await store.create({ title: 'A', description: '' })
    await store.remove(store.tasks.value[0].id)

    store.forgetRemoved()

    expect(store.removed.value).toBeNull()
  })

  it('reopen marks a completed task as pending', async () => {
    await store.create({ title: 'A', description: '' })
    await store.complete(store.tasks.value[0].id)

    await store.reopen(store.tasks.value[0].id)

    expect(store.tasks.value[0].status).toBe('PENDING')
  })

  it('loads one page at a time and loadMore appends the next', async () => {
    for (const title of ['A', 'B', 'C']) await api.create({ title, description: '' })
    store = useTasks(api, { pageSize: 2 })

    await store.load()
    expect(store.tasks.value.map((t) => t.title)).toEqual(['A', 'B'])
    expect(store.total.value).toBe(3)
    expect(store.hasMore.value).toBe(true)

    await store.loadMore()
    expect(store.tasks.value.map((t) => t.title)).toEqual(['A', 'B', 'C'])
    expect(store.hasMore.value).toBe(false)
  })

  it('actions keep the pages already loaded', async () => {
    for (const title of ['A', 'B', 'C']) await api.create({ title, description: '' })
    store = useTasks(api, { pageSize: 2 })
    await store.load()
    await store.loadMore()

    await store.complete(store.tasks.value[0].id)

    expect(store.tasks.value).toHaveLength(3)
  })

  it('changing the filter goes back to the first page', async () => {
    for (const title of ['A', 'B', 'C']) await api.create({ title, description: '' })
    store = useTasks(api, { pageSize: 2 })
    await store.load()
    await store.loadMore()

    await store.setFilter('pending')

    expect(store.tasks.value).toHaveLength(2)
  })

  it('starts with the given initial filter', async () => {
    await api.create({ title: 'A', description: '' })
    store = useTasks(api, { initialFilter: 'completed' })

    await store.load()

    expect(store.filter.value).toBe('completed')
    expect(store.tasks.value).toEqual([])
  })

  it('a task that no longer exists refreshes the list', async () => {
    await store.create({ title: 'A', description: '' })
    const id = store.tasks.value[0].id
    api.tasks = [] // removida "em outra aba"

    await store.complete(id)

    expect(store.tasks.value).toEqual([])
  })

  it('a network failure gets a friendly message', async () => {
    api.list = async () => {
      throw new TypeError('Failed to fetch')
    }

    await store.load()

    expect(store.error.value).toBe('Não foi possível falar com o servidor. Verifique a conexão e tente de novo.')
  })

  it('an unexpected server error gets a generic message', async () => {
    api.list = async () => {
      throw new ApiError('boom', 500)
    }

    await store.load()

    expect(store.error.value).toBe('Algo deu errado no servidor (500). Tente de novo.')
  })

  it('counts pending and completed tasks regardless of the filter', async () => {
    for (const title of ['A', 'B', 'C']) await api.create({ title, description: '' })
    await api.complete(api.tasks[0].id)

    await store.setFilter('completed')

    expect(store.counts.value).toEqual({ all: 3, pending: 2, completed: 1 })
  })

  it('a rate-limited request gets a friendly message', async () => {
    api.create = async () => {
      throw new ApiError('Too many requests. Try again in 12 seconds.', 429)
    }

    await store.create({ title: 'A', description: '' })

    expect(store.error.value).toBe('Muitas ações em pouco tempo. Aguarde alguns segundos e tente de novo.')
  })
})
