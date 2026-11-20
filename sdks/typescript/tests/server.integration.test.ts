import { spawn, type ChildProcess } from 'node:child_process'
import { existsSync, mkdtempSync } from 'node:fs'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import { createTodoClient, iterateTasks } from '../src/index'

const BACKEND = resolve(__dirname, '../../../backend')
const PYTHON = join(BACKEND, '.venv/bin/python')
const servers: ChildProcess[] = []

async function freePort() {
  return new Promise<number>((done) => {
    const server = createServer().listen(0, () => {
      const { port } = server.address() as { port: number }
      server.close(() => done(port))
    })
  })
}

/** Sobe a API de verdade (uvicorn) com banco temporário. */
async function startApi(rateLimit = 'off') {
  const port = await freePort()
  const db = join(mkdtempSync(join(tmpdir(), 'todo-sdk-ts-')), 'todo.db')
  const child = spawn(PYTHON, ['-m', 'uvicorn', 'server:app', '--port', String(port)], {
    cwd: BACKEND,
    env: { ...process.env, TODO_DATABASE: db, TODO_RATE_LIMIT: rateLimit },
    stdio: 'ignore',
  })
  servers.push(child)
  const baseUrl = `http://127.0.0.1:${port}`
  for (let i = 0; i < 100; i++) {
    try {
      if ((await fetch(`${baseUrl}/health`)).ok) return baseUrl
    } catch {
      await new Promise((r) => setTimeout(r, 100))
    }
  }
  throw new Error('uvicorn não subiu')
}

afterEach(() => {
  while (servers.length) servers.pop()!.kill()
})

describe.skipIf(!existsSync(PYTHON))('SDK contra a API real', () => {
  it('cria, conclui, reabre, lista e remove uma tarefa', async () => {
    const client = createTodoClient({ baseUrl: await startApi() })

    const { data: created, response } = await client.POST('/tasks', { body: { title: 'Pelo SDK', description: 'ts' } })
    expect(response.status).toBe(201)
    const path = { params: { path: { task_id: created!.id } } }

    expect((await client.POST('/tasks/{task_id}/complete', path)).data!.status).toBe('COMPLETED')
    expect((await client.POST('/tasks/{task_id}/reopen', path)).data!.status).toBe('PENDING')

    const titles = []
    for await (const t of iterateTasks(client)) titles.push(t.title)
    expect(titles).toEqual(['Pelo SDK'])

    expect((await client.DELETE('/tasks/{task_id}', path)).response.status).toBe(204)
    const missing = await client.GET('/tasks/{task_id}', path)
    expect(missing.response.status).toBe(404)
    expect(missing.error).toMatchObject({ detail: expect.stringContaining('not found') })
  })

  it('espera o Retry-After quando a API limita e completa todas as chamadas', async () => {
    const client = createTodoClient({ baseUrl: await startApi('2/second') })

    const statuses = []
    for (let i = 0; i < 4; i++) statuses.push((await client.GET('/tasks')).response.status)

    expect(statuses).toEqual([200, 200, 200, 200])
  }, 15_000)
})
