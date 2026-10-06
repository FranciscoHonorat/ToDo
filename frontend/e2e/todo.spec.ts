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

test('mostra o erro do backend para título vazio e mantém o que foi digitado', async ({ page }) => {
  await page.goto('/')

  await addTask(page, '   ', 'sem título')

  await expect(page.getByRole('alert')).toHaveText('Title cannot be empty.')
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
