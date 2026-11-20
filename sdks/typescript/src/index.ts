/**
 * SDK TypeScript da ToDo API.
 *
 * - `schema.ts` é GERADO a partir de docs/openapi.yaml (`npm run generate`) — não edite à mão.
 * - Este arquivo é a camada fina escrita à mão: cliente tipado, retry no 429 e paginação.
 */
import createClient, { type Client } from 'openapi-fetch'
import type { components, paths } from './schema'

export type { components, operations, paths } from './schema'
export type Task = components['schemas']['TaskOutput']
export type TaskInput = components['schemas']['TaskInput']
export type TaskStatus = components['schemas']['Status']
export type TodoClient = Client<paths>

export interface RetryOptions {
  /** Quantas vezes repetir depois do primeiro 429 (padrão 3). */
  maxRetries?: number
  /** Não espera mais que isso; se o Retry-After for maior, devolve o 429 (padrão 60 s). */
  maxDelaySeconds?: number
  /** Injetável para testes. */
  sleep?: (ms: number) => Promise<void>
}

export interface TodoClientOptions extends RetryOptions {
  /** Ex.: "http://localhost:8000" ou "http://localhost:8080/api" (atrás do nginx). */
  baseUrl: string
  fetch?: typeof fetch
}

const defaultSleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

/** Envolve um fetch para repetir requisições que recebem 429, esperando o Retry-After. */
export function withRetryOn429(
  fetchFn: typeof fetch,
  { maxRetries = 3, maxDelaySeconds = 60, sleep = defaultSleep }: RetryOptions = {},
): typeof fetch {
  return async (input, init) => {
    // O corpo de um Request só pode ser lido uma vez: cada tentativa usa um clone.
    const request = new Request(input, init)
    for (let attempt = 0; ; attempt++) {
      const response = await fetchFn(request.clone())
      if (response.status !== 429 || attempt >= maxRetries) return response

      const delay = Number(response.headers.get('Retry-After') ?? 1)
      if (!Number.isFinite(delay) || delay > maxDelaySeconds) return response
      await sleep(delay * 1000)
    }
  }
}

export function createTodoClient({ baseUrl, fetch: fetchFn = globalThis.fetch, ...retry }: TodoClientOptions): TodoClient {
  return createClient<paths>({ baseUrl, fetch: withRetryOn429(fetchFn, retry) })
}

/** Percorre todas as tarefas, página por página (limit/offset + X-Total-Count). */
export async function* iterateTasks(
  client: TodoClient,
  { status, pageSize = 100 }: { status?: 'pending' | 'completed'; pageSize?: number } = {},
): AsyncGenerator<Task> {
  for (let offset = 0; ; offset += pageSize) {
    const { data, error, response } = await client.GET('/tasks', {
      params: { query: { status, limit: pageSize, offset } },
    })
    if (error || !data) throw new Error(`GET /tasks falhou com ${response.status}`)
    yield* data

    const total = Number(response.headers.get('X-Total-Count') ?? 0)
    if (data.length < pageSize || offset + data.length >= total) return
  }
}
