import { defineConfig, devices } from '@playwright/test'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const API_PORT = 8001
const WEB_PORT = 5174

// Com E2E_BASE_URL (ex.: http://localhost:8080 do docker compose) os testes rodam
// contra um ambiente já no ar; sem ela, o Playwright sobe API + Vite isolados.
// ATENÇÃO: o beforeEach apaga todas as tarefas — nunca aponte para dados reais.
const EXTERNAL_BASE_URL = process.env.E2E_BASE_URL
const BASE_URL = EXTERNAL_BASE_URL ?? `http://localhost:${WEB_PORT}`
export const API_URL = EXTERNAL_BASE_URL ? `${EXTERNAL_BASE_URL}/api` : `http://localhost:${API_PORT}`

// Banco descartável por execução: o E2E nunca toca em backend/db/todo.db.
process.env.E2E_DATABASE ??= join(tmpdir(), `todo-e2e-${Date.now()}.db`)

export default defineConfig({
  testDir: 'e2e',
  globalTeardown: './e2e/global-teardown.ts',
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 2 : 0,
  reporter: 'list',
  use: {
    baseURL: BASE_URL,
    testIdAttribute: 'data-test',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: EXTERNAL_BASE_URL ? [] : [
    {
      command: `../.venv/bin/python -m uvicorn server:app --port ${API_PORT}`,
      cwd: '../backend',
      env: { TODO_DATABASE: process.env.E2E_DATABASE },
      url: `${API_URL}/tasks`,
      reuseExistingServer: false,
    },
    {
      command: `npx vite --port ${WEB_PORT} --strictPort`,
      env: { API_URL: `http://localhost:${API_PORT}` },
      url: `http://localhost:${WEB_PORT}`,
      reuseExistingServer: false,
    },
  ],
})
