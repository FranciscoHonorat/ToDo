import { describe, expect, it, vi } from 'vitest'
import { createTodoClient, iterateTasks, withRetryOn429 } from '../src/index'

const task = (n: number) => ({ id: `id-${n}`, title: `T${n}`, description: '', status: 'PENDING' as const })

function json(status: number, body: unknown, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } })
}

describe('withRetryOn429', () => {
  it('waits Retry-After seconds and retries until it succeeds', async () => {
    const fetchFn = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(json(429, { detail: 'slow down' }, { 'Retry-After': '2' }))
      .mockResolvedValueOnce(json(200, []))
    const sleep = vi.fn(async () => {})

    const response = await withRetryOn429(fetchFn, { sleep })('http://api/tasks')

    expect(response.status).toBe(200)
    expect(sleep).toHaveBeenCalledWith(2000)
    expect(fetchFn).toHaveBeenCalledTimes(2)
  })

  it('gives up after maxRetries and returns the last 429', async () => {
    const fetchFn = vi.fn<typeof fetch>(async () => json(429, {}, { 'Retry-After': '1' }))

    const response = await withRetryOn429(fetchFn, { maxRetries: 2, sleep: async () => {} })('http://api/tasks')

    expect(response.status).toBe(429)
    expect(fetchFn).toHaveBeenCalledTimes(3)
  })

  it('does not wait longer than maxDelaySeconds', async () => {
    const fetchFn = vi.fn<typeof fetch>(async () => json(429, {}, { 'Retry-After': '3600' }))
    const sleep = vi.fn(async () => {})

    const response = await withRetryOn429(fetchFn, { maxDelaySeconds: 30, sleep })('http://api/tasks')

    expect(response.status).toBe(429)
    expect(sleep).not.toHaveBeenCalled()
  })

  it('resends the request body on retry', async () => {
    const bodies: string[] = []
    const fetchFn = vi.fn<typeof fetch>(async (input) => {
      bodies.push(await (input as Request).text())
      return bodies.length === 1 ? json(429, {}, { 'Retry-After': '0' }) : json(201, task(1))
    })

    await withRetryOn429(fetchFn, { sleep: async () => {} })('http://api/tasks', {
      method: 'POST',
      body: JSON.stringify({ title: 'A' }),
    })

    expect(bodies).toEqual(['{"title":"A"}', '{"title":"A"}'])
  })
})

describe('createTodoClient', () => {
  it('calls the API with typed paths and parameters', async () => {
    const fetchFn = vi.fn<typeof fetch>(async () => json(200, [task(1)], { 'X-Total-Count': '1' }))
    const client = createTodoClient({ baseUrl: 'http://api', fetch: fetchFn })

    const { data } = await client.GET('/tasks', { params: { query: { status: 'pending', limit: 10 } } })

    expect(data).toEqual([task(1)])
    expect((fetchFn.mock.calls[0][0] as Request).url).toBe('http://api/tasks?status=pending&limit=10')
  })
})

describe('iterateTasks', () => {
  it('walks every page using limit/offset until X-Total-Count is reached', async () => {
    const all = [1, 2, 3, 4, 5].map(task)
    const fetchFn = vi.fn<typeof fetch>(async (input) => {
      const url = new URL((input as Request).url)
      const limit = Number(url.searchParams.get('limit'))
      const offset = Number(url.searchParams.get('offset') ?? 0)
      return json(200, all.slice(offset, offset + limit), { 'X-Total-Count': String(all.length) })
    })
    const client = createTodoClient({ baseUrl: 'http://api', fetch: fetchFn })

    const titles: string[] = []
    for await (const t of iterateTasks(client, { pageSize: 2 })) titles.push(t.title)

    expect(titles).toEqual(['T1', 'T2', 'T3', 'T4', 'T5'])
    expect(fetchFn).toHaveBeenCalledTimes(3)
  })

  it('throws when the API answers with an error', async () => {
    const client = createTodoClient({
      baseUrl: 'http://api',
      fetch: async () => json(422, { detail: [{ msg: 'bad' }] }),
    })

    await expect(iterateTasks(client).next()).rejects.toThrow('GET /tasks falhou com 422')
  })
})
