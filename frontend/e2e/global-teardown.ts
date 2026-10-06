import { rmSync } from 'node:fs'

export default function globalTeardown() {
  if (process.env.E2E_DATABASE) rmSync(process.env.E2E_DATABASE, { force: true })
}
