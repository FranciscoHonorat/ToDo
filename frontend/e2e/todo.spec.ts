import { expect, test, type Page } from '@playwright/test'
import { API_URL } from '../playwright.config'

test.beforeEach(async ({ request }) => {
  const tasks: { id: string }[] = await (await request.get(`${API_URL}/tasks`)).json()
  await Promise.all(tasks.map((task) => request.delete(`${API_URL}/tasks/${task.id}`)))
})

async function addTask(page: Page, title: string, description = '') {
  const form = page.getByTestId('new-task')
  await form.getByTestId('title').fill(title)
  await form.getByTestId('description').fill(description)
  await form.getByRole('button', { name: 'Adicionar' }).click()
}

const task = (page: Page, title: string) => page.getByTestId('task').filter({ hasText: title })

test('adiciona uma tarefa e ela continua lá depois de recarregar a página', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('empty')).toHaveText('Nenhuma tarefa.')

  await addTask(page, 'Comprar pão', 'na padaria')

  await expect(task(page, 'Comprar pão')).toContainText('na padaria')
  await expect(page.getByTestId('new-task').getByTestId('title')).toHaveValue('')

  await page.reload()
  await expect(task(page, 'Comprar pão')).toBeVisible()
})

test('barra título vazio no próprio campo e mantém o que foi digitado', async ({ page }) => {
  await page.goto('/')

  await addTask(page, '   ', 'sem título')

  await expect(page.getByTestId('title-error')).toHaveText('Dê um título para a tarefa.')
  await expect(page.getByTestId('new-task').getByTestId('description')).toHaveValue('sem título')
  await expect(page.getByTestId('empty')).toBeVisible()
})

test('conclui uma tarefa e filtra por status', async ({ page }) => {
  await page.goto('/')
  await addTask(page, 'Estudar TDD')
  await addTask(page, 'Lavar louça')

  await task(page, 'Estudar TDD').getByTestId('complete').click()

  await expect(task(page, 'Estudar TDD')).toHaveClass(/done/)
  await expect(task(page, 'Estudar TDD').getByTestId('complete')).toHaveCount(0)

  await page.getByTestId('filter-completed').click()
  await expect(page.getByTestId('task')).toHaveText([/Estudar TDD/])

  await page.getByTestId('filter-pending').click()
  await expect(page.getByTestId('task')).toHaveText([/Lavar louça/])

  await page.getByTestId('filter-all').click()
  await expect(page.getByTestId('task')).toHaveCount(2)
})

test('edita uma tarefa; cancelar descarta a alteração', async ({ page }) => {
  await page.goto('/')
  await addTask(page, 'Ler livro')

  await task(page, 'Ler livro').getByTestId('edit').click()
  await page.getByTestId('task').getByTestId('title').fill('Rascunho')
  await page.getByTestId('cancel').click()
  await expect(task(page, 'Ler livro')).toBeVisible()

  await task(page, 'Ler livro').getByTestId('edit').click()
  await page.getByTestId('task').getByTestId('title').fill('Ler livro de Python')
  await page.getByRole('button', { name: 'Salvar' }).click()

  await expect(task(page, 'Ler livro de Python')).toBeVisible()
  await page.reload()
  await expect(task(page, 'Ler livro de Python')).toBeVisible()
})

test('remove uma tarefa', async ({ page }) => {
  await page.goto('/')
  await addTask(page, 'Temporária')

  await task(page, 'Temporária').getByTestId('remove').click()

  await expect(page.getByTestId('empty')).toBeVisible()
})

test('reabre uma tarefa concluída clicando no check', async ({ page }) => {
  await page.goto('/')
  await addTask(page, 'Pagar boleto')
  await task(page, 'Pagar boleto').getByTestId('complete').click()
  await expect(task(page, 'Pagar boleto')).toHaveClass(/done/)

  await task(page, 'Pagar boleto').getByTestId('reopen').click()

  await expect(task(page, 'Pagar boleto')).not.toHaveClass(/done/)
  await page.reload()
  await expect(task(page, 'Pagar boleto').getByTestId('complete')).toBeVisible()
})

test('o filtro fica na URL e sobrevive a recarregar a página', async ({ page }) => {
  await page.goto('/')
  await addTask(page, 'Feita')
  await addTask(page, 'Por fazer')
  await task(page, 'Feita').getByTestId('complete').click()

  await page.getByTestId('filter-completed').click()
  await expect(page).toHaveURL(/\?status=completed$/)
  await page.reload()

  await expect(page.getByTestId('task')).toHaveText([/Feita/])
  await expect(page.getByTestId('filter-completed')).toHaveAttribute('aria-pressed', 'true')
})

test('desfaz uma remoção', async ({ page }) => {
  await page.goto('/')
  await addTask(page, 'Importante')

  await task(page, 'Importante').getByTestId('remove').click()
  await page.getByTestId('undo').click()

  await expect(task(page, 'Importante')).toBeVisible()
  await page.reload()
  await expect(task(page, 'Importante')).toBeVisible()
})

test('carrega a lista em páginas', async ({ page, request }) => {
  for (let i = 1; i <= 25; i++) {
    await request.post(`${API_URL}/tasks`, { data: { title: `Tarefa ${i}`, description: '' } })
  }
  await page.goto('/')

  await expect(page.getByTestId('task')).toHaveCount(20)
  await expect(page.getByTestId('filter-all')).toHaveText('Todas 25')

  await page.getByTestId('load-more').click()

  await expect(page.getByTestId('task')).toHaveCount(25)
  await expect(page.getByTestId('load-more')).toHaveCount(0)
})
