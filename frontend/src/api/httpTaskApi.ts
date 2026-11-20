import { ApiError, type ListQuery, type Task, type TaskApi, type TaskInput, type TaskPage } from './types'

type Fetch = typeof fetch

export function createHttpTaskApi(baseUrl: string, fetchFn: Fetch = fetch): TaskApi {
  async function send(method: string, path: string, body?: unknown) {
    const init: RequestInit = { method }
    if (body !== undefined) {
      init.headers = { 'Content-Type': 'application/json' }
      init.body = JSON.stringify(body)
    }

    const response = await fetchFn(`${baseUrl}${path}`, init)
    const data = parseJson(await response.text())

    if (!response.ok) {
      const detail = (data as { detail?: unknown } | undefined)?.detail
      const message = typeof detail === 'string' ? detail : `Requisição inválida (${response.status}).`
      throw new ApiError(message, response.status)
    }
    return { data, response }
  }

  async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
    return (await send(method, path, body)).data as T
  }

  async function list({ status, limit, offset }: ListQuery = {}): Promise<TaskPage> {
    const params = new URLSearchParams()
    if (status) params.set('status', status)
    if (limit !== undefined) params.set('limit', String(limit))
    if (offset) params.set('offset', String(offset))
    const query = params.size ? `?${params}` : ''

    const { data, response } = await send('GET', `/tasks${query}`)
    const items = data as Task[]
    const total = Number(response.headers.get('X-Total-Count') ?? items.length)
    return { items, total }
  }

  return {
    list,
    create: (input: TaskInput) => request<Task>('POST', '/tasks', input),
    edit: (id: string, input: TaskInput) => request<Task>('PUT', `/tasks/${id}`, input),
    complete: (id: string) => request<Task>('POST', `/tasks/${id}/complete`),
    reopen: (id: string) => request<Task>('POST', `/tasks/${id}/reopen`),
    remove: (id: string) => request<void>('DELETE', `/tasks/${id}`),
  }
}

/** Respostas de erro do proxy (ex.: 502 do nginx) vêm em HTML — não podem quebrar o tratamento de erro. */
function parseJson(text: string): unknown {
  if (!text) return undefined
  try {
    return JSON.parse(text)
  } catch {
    return undefined
  }
}
