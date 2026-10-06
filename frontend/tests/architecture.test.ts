import { readdirSync, readFileSync } from 'node:fs'
import { join, relative } from 'node:path'
import { describe, expect, it } from 'vitest'

const SRC = join(__dirname, '..', 'src')

/** Mapa "arquivo relativo a src" -> lista de imports desse arquivo. */
const imports = Object.fromEntries(
  readdirSync(SRC, { recursive: true, encoding: 'utf8' })
    .filter((file) => /\.(ts|vue)$/.test(file))
    .map((file) => {
      const source = readFileSync(join(SRC, file), 'utf8')
      const found = [...source.matchAll(/import\s[^'"]*['"]([^'"]+)['"]/g)].map((m) => m[1])
      return [relative(SRC, join(SRC, file)), found]
    }),
)

function filesIn(folder: string) {
  return Object.keys(imports).filter((file) => file.startsWith(`${folder}/`))
}

function violations(files: string[], forbidden: RegExp) {
  return files.flatMap((file) => imports[file].filter((i) => forbidden.test(i)).map((i) => `${file} -> ${i}`))
}

describe('arquitetura do frontend', () => {
  it('encontrou os arquivos de src (sanidade do próprio teste)', () => {
    expect(filesIn('components').length).toBeGreaterThan(0)
    expect(filesIn('api').length).toBeGreaterThan(0)
  })

  it('src/api não conhece Vue nem a camada de tela', () => {
    expect(violations(filesIn('api'), /^vue$|composables|components/)).toEqual([])
  })

  it('composables não importam componentes', () => {
    expect(violations(filesIn('composables'), /components|\.vue$/)).toEqual([])
  })

  it('componentes não falam com a API diretamente — recebem tudo por props (DIP)', () => {
    expect(violations(filesIn('components'), /httpTaskApi|composables/)).toEqual([])
  })

  it('só a composition root (main.ts) conhece a implementação HTTP', () => {
    const users = Object.keys(imports).filter((file) => imports[file].some((i) => i.includes('httpTaskApi')))

    expect(users).toEqual(['main.ts'])
  })
})
