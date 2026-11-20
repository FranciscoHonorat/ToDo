import { describe, expect, it, vi } from 'vitest'
import { createHttpTaskApi } from '../src/api/httpTaskApi'
import { ApiError } from '../src/api/types'

const task = { id: '1', title: 'Comprar pão', description: '', status: 'PENDING' }

function fakeFetch(status: number, body?: unknown, headers: Record<string, string> = {}) {
  return vi.fn(async () =>
    new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json', ...headers },
    }),
  )
}

describe('createHttpTaskApi', () => {
  it('lists tasks with GET /tasks and reads the total from X-Total-Count', async () => {
    const fetch = fakeFetch(200, [task], { 'X-Total-Count': '7' })
    const api = createHttpTaskApi('/api', fetch)

    expect(await api.list()).toEqual({ items: [task], total: 7 })
    expect(fetch).toHaveBeenCalledWith('/api/tasks', expect.objectContaining({ method: 'GET' }))
  })

  it('falls back to the number of items when X-Total-Count is missing', async () => {
    const api = createHttpTaskApi('/api', fakeFetch(200, [task]))

    expect((await api.list()).total).toBe(1)
  })

  it('sends status, limit and offset as query string', async () => {
    const fetch = fakeFetch(200, [])
    const api = createHttpTaskApi('/api', fetch)

    await api.list({ status: 'completed', limit: 20, offset: 40 })

    expect(fetch).toHaveBeenCalledWith('/api/tasks?status=completed&limit=20&offset=40', expect.anything())
  })

  it('creates a task with POST and a JSON body', async () => {
    const fetch = fakeFetch(201, task)
    const api = createHttpTaskApi('/api', fetch)

    await api.create({ title: 'Comprar pão', description: '' })

    expect(fetch).toHaveBeenCalledWith('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: 'Comprar pão', description: '' }),
    })
  })

  it('edits a task with PUT /tasks/:id', async () => {
    const fetch = fakeFetch(200, task)
    const api = createHttpTaskApi('/api', fetch)

    await api.edit('1', { title: 'Novo', description: 'nova' })

    expect(fetch).toHaveBeenCalledWith('/api/tasks/1', expect.objectContaining({ method: 'PUT' }))
  })

  it('completes a task with POST /tasks/:id/complete', async () => {
    const fetch = fakeFetch(200, { ...task, status: 'COMPLETED' })
    const api = createHttpTaskApi('/api', fetch)

    expect((await api.complete('1')).status).toBe('COMPLETED')
    expect(fetch).toHaveBeenCalledWith('/api/tasks/1/complete', expect.objectContaining({ method: 'POST' }))
  })

  it('reopens a task with POST /tasks/:id/reopen', async () => {
    const fetch = fakeFetch(200, task)
    const api = createHttpTaskApi('/api', fetch)

    expect((await api.reopen('1')).status).toBe('PENDING')
    expect(fetch).toHaveBeenCalledWith('/api/tasks/1/reopen', expect.objectContaining({ method: 'POST' }))
  })

  it('removes a task with DELETE and accepts an empty 204 body', async () => {
    const fetch = fakeFetch(204)
    const api = createHttpTaskApi('/api', fetch)

    await expect(api.remove('1')).resolves.toBeUndefined()
    expect(fetch).toHaveBeenCalledWith('/api/tasks/1', expect.objectContaining({ method: 'DELETE' }))
  })

  it('turns an error response into an ApiError with the backend detail', async () => {
    const api = createHttpTaskApi('/api', fakeFetch(422, { detail: 'Title cannot be empty.' }))

    const error = await api.create({ title: ' ', description: '' }).catch((e) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error.message).toBe('Title cannot be empty.')
    expect(error.status).toBe(422)
  })

  it('uses a generic message when the detail is not a string', async () => {
    const api = createHttpTaskApi('/api', fakeFetch(422, { detail: [{ msg: 'x' }] }))

    await expect(api.list()).rejects.toThrow('Requisição inválida (422).')
  })

  it('a non-JSON error body (e.g. 502 from the proxy) still becomes an ApiError', async () => {
    const fetch = vi.fn(async () => new Response('<html>Bad Gateway</html>', { status: 502 }))
    const api = createHttpTaskApi('/api', fetch)

    const error = await api.list().catch((e) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(502)
  })
})
