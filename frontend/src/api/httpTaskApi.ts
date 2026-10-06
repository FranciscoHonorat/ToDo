import { ApiError, type StatusFilter, type Task, type TaskApi, type TaskInput } from './types'

type Fetch = typeof fetch

export function createHttpTaskApi(baseUrl: string, fetchFn: Fetch = fetch): TaskApi {
  async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const init: RequestInit = { method }
    if (body !== undefined) {
      init.headers = { 'Content-Type': 'application/json' }
      init.body = JSON.stringify(body)
    }

    const response = await fetchFn(`${baseUrl}${path}`, init)
    const text = await response.text()
    const data = text ? JSON.parse(text) : undefined

    if (!response.ok) {
      const detail = data?.detail
      const message = typeof detail === 'string' ? detail : `Requisição inválida (${response.status}).`
      throw new ApiError(message, response.status)
    }
    return data as T
  }

  return {
    list: (status?: StatusFilter) => request<Task[]>('GET', status ? `/tasks?status=${status}` : '/tasks'),
    create: (input: TaskInput) => request<Task>('POST', '/tasks', input),
    edit: (id: string, input: TaskInput) => request<Task>('PUT', `/tasks/${id}`, input),
    complete: (id: string) => request<Task>('POST', `/tasks/${id}/complete`),
    remove: (id: string) => request<void>('DELETE', `/tasks/${id}`),
  }
}
