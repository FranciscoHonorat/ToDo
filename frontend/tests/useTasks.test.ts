import { beforeEach, describe, expect, it } from 'vitest'
import { useTasks } from '../src/composables/useTasks'
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
    expect(store.error.value).toBe('Title cannot be empty.')
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

    expect(store.error.value).toBe('Task with ID nope not found.')
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
})
